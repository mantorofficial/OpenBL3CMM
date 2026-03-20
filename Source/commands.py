"""
Simple command syntax for BL3 hotfix modding.

Instead of raw SparkPatchEntry lines, users can write:
    set /Game/Path/Object Property Value
    set_cmp /Game/Path/Object Property OldValue NewValue
    clone /Game/Source/Object /Game/Dest/Object
    delete /Game/Path/Object
    create /Game/Path/Object ClassName
    set_array /Game/Path/Object ArrayProp (elem1, elem2, ...)
    add /Game/Path/Object ArrayProp NewElement
    remove /Game/Path/Object ArrayProp ElementToRemove
    set_if /Game/Path/Object Property ConditionValue NewValue
    set_struct /Game/Path/Object StructProp.Field Value
    edit /Game/Path/Object Property Value         (level-specific, MatchAll)
    exec other_mod.bl3hotfix
    rename /Game/Path/Object NewName
    merge /Game/Path/Object Property Value        (character-loaded)

These get converted to/from the raw Spark format for OHL/B3HM compatibility.
"""
from __future__ import annotations


# ──────────────────────────────────────────────
# Simple command → Spark hotfix conversion
# ──────────────────────────────────────────────

def simple_to_spark(line: str) -> str | None:
    """
    Convert a simple command to a Spark hotfix line.
    Returns None if the line isn't a recognized simple command.
    """
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None

    parts = stripped.split(None, 1)
    if not parts:
        return None

    cmd = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    handler = COMMAND_MAP.get(cmd)
    if handler:
        return handler(args)
    return None


def spark_to_simple(spark_line: str) -> str | None:
    """
    Convert a Spark hotfix line to the simplest equivalent simple command.
    Returns None if it can't be simplified.
    """
    stripped = spark_line.strip()
    if not stripped:
        return None

    comma_idx = stripped.find(",")
    if comma_idx == -1:
        return None

    htype = stripped[:comma_idx]

    if htype == "InjectNewsItem":
        rest = stripped[comma_idx + 1:]
        return f"news {rest}"

    # Parse out the params and fields
    rest = stripped[comma_idx + 1:]

    # Extract params (...)
    params = ""
    if rest.startswith("("):
        depth = 0
        for i, ch in enumerate(rest):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    params = rest[:i + 1]
                    rest = rest[i + 1:]
                    if rest.startswith(","):
                        rest = rest[1:]
                    break

    # Split remaining: object,attribute,dtkey,index,,value
    fields = rest.split(",", 4)
    obj = fields[0] if len(fields) > 0 else ""
    attr = fields[1] if len(fields) > 1 else ""
    dtkey = fields[2] if len(fields) > 2 else ""
    index = fields[3] if len(fields) > 3 else "0"
    value = ""
    if len(fields) > 4:
        value = fields[4]
        if value.startswith(","):
            value = value[1:]

    # Determine command name and whether to include params
    cmd = ""
    default_params = ""

    if htype == "SparkPatchEntry":
        cmd = "set"
        default_params = "(1,1,0,)"
    elif htype == "SparkLevelPatchEntry":
        cmd = "edit"
        default_params = "(1,2,0,MatchAll)"
    elif htype == "SparkCharacterLoadedEntry":
        cmd = "merge"
        default_params = ""  # always show params for merge
    elif htype == "SparkEarlyLevelPatchEntry":
        cmd = "early_set"
        default_params = "(1,1,0,)"
    else:
        return None

    # Build the simple command
    parts = [cmd]

    # Include params if non-default
    if params and params != default_params:
        parts.append(params)

    # Handle merge's character name from params
    if htype == "SparkCharacterLoadedEntry":
        char = ""
        if params:
            inner = params.strip("()")
            param_parts = inner.split(",")
            if len(param_parts) >= 4 and param_parts[3]:
                char = param_parts[3]
        if char:
            parts.append(f"[{char}]")

    parts.append(obj)
    if attr:
        parts.append(attr)
    if dtkey:
        parts.append(dtkey)
    if index and index != "0":
        parts.append(index)
    elif dtkey:
        # If we have a dtkey, always include index for clarity
        parts.append(index)
    if value:
        parts.append(value)

    return " ".join(parts)


# ──────────────────────────────────────────────
# Individual command handlers
# ──────────────────────────────────────────────

def _parse_obj_attr_val(args: str, min_parts: int = 3) -> tuple[str, str, str] | None:
    """Parse 'object attribute value' from args, where value can contain spaces."""
    parts = args.split(None, 2)
    if len(parts) < min_parts:
        return None
    obj = parts[0]
    attr = parts[1] if len(parts) > 1 else ""
    val = parts[2] if len(parts) > 2 else ""
    return obj, attr, val


def _extract_params(args: str) -> tuple[str, str]:
    """
    If args starts with (...), extract it as custom params and return (params, remaining_args).
    Otherwise return default params and the full args.
    """
    stripped = args.strip()
    if stripped.startswith("("):
        depth = 0
        for i, ch in enumerate(stripped):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    params = stripped[:i + 1]
                    remaining = stripped[i + 1:].strip()
                    return params, remaining
    return "", stripped


def _build_spark(htype: str, params: str, obj: str, attr: str, dtkey: str, index: str, value: str) -> str:
    """Build a properly formatted Spark hotfix line: Type,Params,Object,Attribute,DTKey,Index,,Value"""
    return f"{htype},{params},{obj},{attr},{dtkey},{index},,{value}"


def _cmd_set(args: str) -> str | None:
    """set [params] /Game/Path/Object Property [DTKey] [Index] Value"""
    params, args = _extract_params(args)
    if not params:
        params = "(1,1,0,)"

    parts = args.split()
    if len(parts) < 3:
        return None

    obj = parts[0]
    attr = parts[1]
    # Remaining parts: could be just Value, or DTKey Index Value, or DTKey Value
    remaining = parts[2:]

    if len(remaining) >= 3:
        # DTKey Index Value (value can have spaces)
        dtkey = remaining[0]
        index = remaining[1]
        value = " ".join(remaining[2:])
    elif len(remaining) == 2:
        # Could be DTKey Value or Index Value — check if first looks like an index (pure number)
        if remaining[0].isdigit() and not remaining[1].isdigit():
            dtkey = ""
            index = remaining[0]
            value = remaining[1]
        else:
            dtkey = remaining[0]
            index = "0"
            value = remaining[1]
    else:
        dtkey = ""
        index = "0"
        value = remaining[0]

    return _build_spark("SparkPatchEntry", params, obj, attr, dtkey, index, value)


def _cmd_set_cmp(args: str) -> str | None:
    """set_cmp [params] /Game/Path/Object Property OldValue NewValue"""
    params, args = _extract_params(args)
    if not params:
        params = "(1,1,0,)"
    parts = args.split(None, 3)
    if len(parts) < 4:
        return None
    obj, attr, _old_val, new_val = parts[0], parts[1], parts[2], parts[3]
    return _build_spark("SparkPatchEntry", params, obj, attr, "", "0", new_val)


def _cmd_clone(args: str) -> str | None:
    """clone /Game/Source/Object /Game/Dest/Object"""
    parts = args.split(None, 1)
    if len(parts) < 2:
        return None
    src, dest = parts[0], parts[1]
    return _build_spark("SparkPatchEntry", "(1,1,0,)", dest, "", "", "0", src)


def _cmd_delete(args: str) -> str | None:
    """delete /Game/Path/Object"""
    obj = args.strip()
    if not obj:
        return None
    return _build_spark("SparkPatchEntry", "(1,1,0,)", obj, "", "", "0", "")


def _cmd_create(args: str) -> str | None:
    """create /Game/Path/Object ClassName"""
    parts = args.split(None, 1)
    if len(parts) < 2:
        return None
    obj, classname = parts[0], parts[1]
    return _build_spark("SparkPatchEntry", "(1,1,0,)", obj, "", "", "0", classname)


def _cmd_set_array(args: str) -> str | None:
    """set_array [params] /Game/Path/Object ArrayProp (elem1, elem2, ...)"""
    params, args = _extract_params(args)
    if not params:
        params = "(1,1,0,)"
    result = _parse_obj_attr_val(args)
    if not result:
        return None
    obj, attr, val = result
    return _build_spark("SparkPatchEntry", params, obj, attr, "", "0", val)


def _cmd_add(args: str) -> str | None:
    """add [params] /Game/Path/Object ArrayProp NewElement"""
    params, args = _extract_params(args)
    if not params:
        params = "(1,1,0,)"
    result = _parse_obj_attr_val(args)
    if not result:
        return None
    obj, attr, val = result
    return _build_spark("SparkPatchEntry", params, obj, attr, "", "0", val)


def _cmd_remove(args: str) -> str | None:
    """remove [params] /Game/Path/Object ArrayProp ElementToRemove"""
    params, args = _extract_params(args)
    if not params:
        params = "(1,1,0,)"
    result = _parse_obj_attr_val(args)
    if not result:
        return None
    obj, attr, val = result
    return _build_spark("SparkPatchEntry", params, obj, attr, "", "0", "")


def _cmd_set_if(args: str) -> str | None:
    """set_if [params] /Game/Path/Object Property ConditionValue NewValue"""
    params, args = _extract_params(args)
    if not params:
        params = "(1,1,0,)"
    parts = args.split(None, 3)
    if len(parts) < 4:
        return None
    obj, attr, _cond, new_val = parts[0], parts[1], parts[2], parts[3]
    return _build_spark("SparkPatchEntry", params, obj, attr, "", "0", new_val)


def _cmd_set_struct(args: str) -> str | None:
    """set_struct [params] /Game/Path/Object StructProp.Field Value"""
    params, args = _extract_params(args)
    if not params:
        params = "(1,1,0,)"
    result = _parse_obj_attr_val(args)
    if not result:
        return None
    obj, attr, val = result
    return _build_spark("SparkPatchEntry", params, obj, attr, "", "0", val)


def _cmd_edit(args: str) -> str | None:
    """edit [params] /Game/Path/Object Property [DTKey] [Index] Value"""
    params, args = _extract_params(args)
    if not params:
        params = "(1,2,0,MatchAll)"

    parts = args.split()
    if len(parts) < 3:
        return None

    obj = parts[0]
    attr = parts[1]
    remaining = parts[2:]

    if len(remaining) >= 3:
        dtkey = remaining[0]
        index = remaining[1]
        value = " ".join(remaining[2:])
    elif len(remaining) == 2:
        if remaining[0].isdigit() and not remaining[1].isdigit():
            dtkey = ""
            index = remaining[0]
            value = remaining[1]
        else:
            dtkey = remaining[0]
            index = "0"
            value = remaining[1]
    else:
        dtkey = ""
        index = "0"
        value = remaining[0]

    return _build_spark("SparkLevelPatchEntry", params, obj, attr, dtkey, index, value)


def _cmd_exec(args: str) -> str | None:
    """exec other_mod.bl3hotfix"""
    filename = args.strip()
    if not filename:
        return None
    return f"exec {filename}"


def _cmd_rename(args: str) -> str | None:
    """rename /Game/Path/Object NewName"""
    parts = args.split(None, 1)
    if len(parts) < 2:
        return None
    obj, new_name = parts[0], parts[1]
    return _build_spark("SparkPatchEntry", "(1,1,0,)", obj, "ObjectName", "", "0", new_name)


def _cmd_merge(args: str) -> str | None:
    """merge [CharName] /Game/Path/Object Property Value  (character-loaded)"""
    args = args.strip()
    char = ""
    if args.startswith("["):
        bracket_end = args.find("]")
        if bracket_end != -1:
            char = args[1:bracket_end]
            args = args[bracket_end + 1:].strip()

    result = _parse_obj_attr_val(args)
    if not result:
        return None
    obj, attr, val = result

    if char:
        return _build_spark("SparkCharacterLoadedEntry", f"(1,1,0,{char})", obj, attr, "", "0", val)
    return _build_spark("SparkCharacterLoadedEntry", "(1,1,0,)", obj, attr, "", "0", val)


# ──────────────────────────────────────────────
# Command registry
# ──────────────────────────────────────────────

def _cmd_early_set(args: str) -> str | None:
    """early_set [params] /Game/Path/Object Property [DTKey] [Index] Value"""
    params, args = _extract_params(args)
    if not params:
        params = "(1,1,0,)"

    parts = args.split()
    if len(parts) < 3:
        return None

    obj = parts[0]
    attr = parts[1]
    remaining = parts[2:]

    if len(remaining) >= 3:
        dtkey = remaining[0]
        index = remaining[1]
        value = " ".join(remaining[2:])
    elif len(remaining) == 2:
        if remaining[0].isdigit() and not remaining[1].isdigit():
            dtkey = ""
            index = remaining[0]
            value = remaining[1]
        else:
            dtkey = remaining[0]
            index = "0"
            value = remaining[1]
    else:
        dtkey = ""
        index = "0"
        value = remaining[0]

    return _build_spark("SparkEarlyLevelPatchEntry", params, obj, attr, dtkey, index, value)


def _cmd_news(args: str) -> str | None:
    """news <header>,<image_url>,<article_url>,<body>"""
    content = args.strip()
    if not content:
        return None
    return f"InjectNewsItem,{content}"


COMMAND_MAP = {
    "set":        _cmd_set,
    "set_cmp":    _cmd_set_cmp,
    "clone":      _cmd_clone,
    "delete":     _cmd_delete,
    "create":     _cmd_create,
    "set_array":  _cmd_set_array,
    "add":        _cmd_add,
    "remove":     _cmd_remove,
    "set_if":     _cmd_set_if,
    "set_struct": _cmd_set_struct,
    "edit":       _cmd_edit,
    "early_set":  _cmd_early_set,
    "news":       _cmd_news,
    "exec":       _cmd_exec,
    "rename":     _cmd_rename,
    "merge":      _cmd_merge,
}

SIMPLE_COMMANDS = list(COMMAND_MAP.keys())


# ──────────────────────────────────────────────
# Help text for each command
# ──────────────────────────────────────────────

COMMAND_HELP = {
    "set":        "set [params] <object> <property> [DTKey] [Index] <value>\n  Set a property on an object (SparkPatchEntry).",
    "set_cmp":    "set_cmp [params] <object> <property> <old_value> <new_value>\n  Set only if current value matches old_value.",
    "clone":      "clone <source_object> <dest_object>\n  Clone an object to a new path.",
    "delete":     "delete <object>\n  Delete/clear an object.",
    "create":     "create <object> <class_name>\n  Create a new object of the given class.",
    "set_array":  "set_array [params] <object> <property> <(elements...)>\n  Set an entire array property.",
    "add":        "add [params] <object> <array_property> <new_element>\n  Add an element to an array.",
    "remove":     "remove [params] <object> <array_property> <element>\n  Remove an element from an array.",
    "set_if":     "set_if [params] <object> <property> <condition> <new_value>\n  Conditionally set a property.",
    "set_struct": "set_struct [params] <object> <struct.field> <value>\n  Set a field within a struct property.",
    "edit":       "edit [params] <object> <property> [DTKey] [Index] <value>\n  Level-specific patch (SparkLevelPatchEntry, default MatchAll).",
    "early_set":  "early_set [params] <object> <property> [DTKey] [Index] <value>\n  Early level patch (SparkEarlyLevelPatchEntry).",
    "news":       "news <header>,<image_url>,<article_url>,<body>\n  Inject a news item (InjectNewsItem).",
    "exec":       "exec <filename>\n  Execute/include another mod file.",
    "rename":     "rename <object> <new_name>\n  Rename an object.",
    "merge":      "merge [CharName] <object> <property> <value>\n  Character-loaded patch (SparkCharacterLoadedEntry).",
}