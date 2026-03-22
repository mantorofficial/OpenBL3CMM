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
    # Check internal commands (set_dt, edit_dt — not shown in UI but supported)
    handler = _INTERNAL_COMMANDS.get(cmd)
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

    # Check the hotfix type number from params
    # (1,TYPE,NOTIFY,TARGET) — Type 2 is DataTable, has different field layout
    hotfix_type_num = 1
    if params:
        inner = params.strip("()")
        param_parts = inner.split(",")
        if len(param_parts) >= 2:
            try:
                hotfix_type_num = int(param_parts[1])
            except ValueError:
                pass

    # Type 2 (DataTable) has layout: object,rowname,columnname,fromlength,fromvalue,tovalue
    if hotfix_type_num == 2:
        # DataTable format: object,rowname,columnname,fromlength,fromvalue,tovalue
        fields = rest.split(",", 5)
        obj = fields[0] if len(fields) > 0 else ""
        row_name = fields[1] if len(fields) > 1 else ""
        col_name = fields[2] if len(fields) > 2 else ""
        # fields[3] = from_length, fields[4] = from_value (skip these)
        value = ""
        if len(fields) > 5:
            value = fields[5]
        elif len(fields) > 4:
            remaining = fields[4] if len(fields) > 4 else ""
            if remaining.startswith(","):
                value = remaining[1:]
            else:
                value = remaining

        cmd = "set" if htype == "SparkPatchEntry" else "edit"
        # Show clean form: set <Table> <Row> <Value>
        # Column name is hidden — preserved in raw_line and restored on save
        parts = [cmd, obj, row_name, value]
        return " ".join(p for p in parts if p)

    if hotfix_type_num != 1:
        return None

    # Type 1 layout: object,attribute,from_length,from_value,to_value
    # The from_length and from_value are for set_cmp (conditional set).
    # For simple set: from_length=0, from_value is empty.
    fields = rest.split(",", 4)
    obj = fields[0] if len(fields) > 0 else ""
    attr = fields[1] if len(fields) > 1 else ""
    from_length = fields[2] if len(fields) > 2 else "0"
    value = ""
    if len(fields) > 4:
        # fields[3] = from_value, fields[4] = to_value
        value = fields[4]
    elif len(fields) > 3:
        # fields[3] might be ",to_value" if from_value was empty
        remaining = fields[3]
        if remaining.startswith(","):
            value = remaining[1:]
        else:
            value = remaining

    from_value = ""
    try:
        fl = int(from_length)
        if fl > 0 and len(fields) > 3:
            from_value = fields[3]
            if len(fields) > 4:
                value = fields[4]
    except ValueError:
        pass

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

    # For set_cmp (has a from_value), show both old and new values
    if from_value:
        parts.append(from_value)

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
    # Auto-detect DTKey from datapack if not provided
    if not dtkey:
        dtkey = _auto_detect_dtkey(obj, attr)
    return f"{htype},{params},{obj},{attr},{dtkey},{index},,{value}"


def _auto_detect_dtkey(obj_path: str, attr: str) -> str:
    """
    Try to auto-detect the DataTable row key for an object+attribute.
    Looks up the object in the datapack and finds the struct key under the attribute.
    Returns empty string if not found or not a DataTable.
    """
    try:
        from hotfix_highlighter import get_datapack
        db = get_datapack()
        if not db:
            return ""

        obj = db.get_object(obj_path)
        if not obj:
            return ""

        props = obj.get("properties", {})
        if not props:
            return ""

        # Handle JSON that's a list (JohnWickParse format: list of exports)
        data = props
        if isinstance(data, list):
            # Find the main export (usually first one with properties)
            for export in data:
                if isinstance(export, dict) and export.get("export_type") in ("DataTable", "RowStruct"):
                    data = export
                    break
            else:
                # Just use the first dict
                for export in data:
                    if isinstance(export, dict):
                        data = export
                        break

        if not isinstance(data, dict):
            return ""

        # Check if this attribute exists in the data
        row_data = data.get(attr)
        if not isinstance(row_data, dict):
            return ""

        # The DTKey is the key inside the row struct that's NOT 'export_type'
        # It's typically something like 'Base_2_5C32556442B4DA4D7EAE1A8610E0A950'
        for key in row_data:
            if key == "export_type":
                continue
            # DTKeys are typically long hex-suffixed names
            if "_" in key and len(key) > 20:
                return key

        # If no long key found, check any key that's not export_type
        for key in row_data:
            if key != "export_type":
                return key

    except Exception:
        pass

    return ""


def _cmd_set(args: str) -> str | None:
    """set [params] /Game/Path/Object Property Value"""
    params, args = _extract_params(args)
    if not params:
        params = "(1,1,0,)"

    parts = args.split(None, 2)
    if len(parts) < 3:
        return None

    obj = parts[0]
    attr = parts[1]
    value = parts[2]

    # Type 1: object,attribute,from_length,from_value,to_value
    # For unconditional set: from_length=0, from_value empty
    return f"{_htype_for_params(params)},{params},{obj},{attr},0,,{value}"


def _htype_for_params(params: str) -> str:
    """Determine hotfix type string from params."""
    if "MatchAll" in params or params.count(",") >= 3 and params.split(",")[3].strip(")"):
        # Has a target — check if it looks like a level or character
        inner = params.strip("()")
        pp = inner.split(",")
        if len(pp) >= 4 and pp[3]:
            # Could be level or character — default to SparkPatchEntry
            pass
    return "SparkPatchEntry"


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
    """edit [params] /Game/Path/Object Property Value"""
    params, args = _extract_params(args)
    if not params:
        params = "(1,1,0,MatchAll)"

    parts = args.split(None, 2)
    if len(parts) < 3:
        return None

    obj = parts[0]
    attr = parts[1]
    value = parts[2]

    return f"SparkLevelPatchEntry,{params},{obj},{attr},0,,{value}"


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
    return f"SparkPatchEntry,(1,1,0,),{obj},ObjectName,0,,{new_name}"


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
        return f"SparkCharacterLoadedEntry,(1,1,0,{char}),{obj},{attr},0,,{val}"
    return f"SparkCharacterLoadedEntry,(1,1,0,),{obj},{attr},0,,{val}"


# ──────────────────────────────────────────────
# Command registry
# ──────────────────────────────────────────────

def _cmd_early_set(args: str) -> str | None:
    """early_set [params] /Game/Path/Object Property Value"""
    params, args = _extract_params(args)
    if not params:
        params = "(1,1,0,)"

    parts = args.split(None, 2)
    if len(parts) < 3:
        return None

    obj = parts[0]
    attr = parts[1]
    value = parts[2]

    return f"SparkEarlyLevelPatchEntry,{params},{obj},{attr},0,,{value}"


def _cmd_news(args: str) -> str | None:
    """news <header>,<image_url>,<article_url>,<body>"""
    content = args.strip()
    if not content:
        return None
    return f"InjectNewsItem,{content}"


def _cmd_set_dt(args: str) -> str | None:
    """set_dt <DataTable> <RowName> [ColumnName] <Value>
    DataTable hotfix (Type 2) — edits a cell in a DataTable.
    If ColumnName is omitted, auto-detects from the datapack.
    """
    parts = args.split(None, 3)
    if len(parts) < 3:
        return None

    if len(parts) == 3:
        # 3 args: table, row, value — auto-detect column
        obj, row, value = parts[0], parts[1], parts[2]
        col = _auto_detect_dt_column(obj, row)
        if not col:
            return None
    else:
        # 4 args: table, row, column, value
        obj, row, col, value = parts[0], parts[1], parts[2], parts[3]
        # Check if parts[2] looks like a column name (has hex hash) or is actually the value
        if "_" not in col or len(col) < 20:
            # Probably not a column name — treat as 3 args
            value = col + " " + value if value else col
            col = _auto_detect_dt_column(obj, row)
            if not col:
                return None

    return f"SparkPatchEntry,(1,2,0,),{obj},{row},{col},0,,{value}"


def _cmd_edit_dt(args: str) -> str | None:
    """edit_dt <DataTable> <RowName> [ColumnName] <Value>
    Level-based DataTable hotfix (Type 2, MatchAll).
    """
    parts = args.split(None, 3)
    if len(parts) < 3:
        return None

    if len(parts) == 3:
        obj, row, value = parts[0], parts[1], parts[2]
        col = _auto_detect_dt_column(obj, row)
        if not col:
            return None
    else:
        obj, row, col, value = parts[0], parts[1], parts[2], parts[3]
        if "_" not in col or len(col) < 20:
            value = col + " " + value if value else col
            col = _auto_detect_dt_column(obj, row)
            if not col:
                return None

    return f"SparkLevelPatchEntry,(1,2,0,MatchAll),{obj},{row},{col},0,,{value}"


def _auto_detect_dt_column(table_path: str, row_name: str) -> str:
    """Auto-detect the column name for a DataTable row from the datapack."""
    try:
        from hotfix_highlighter import get_datapack
        db = get_datapack()
        if not db:
            return ""

        # Strip the .TableName suffix if present for lookup
        base_path = table_path.split(".")[0] if "." in table_path else table_path
        obj = db.get_object(base_path)
        if not obj:
            return ""

        import json, zlib
        props = obj.get("properties")
        if isinstance(props, bytes):
            props = json.loads(zlib.decompress(props))
        if not props:
            return ""

        # JWP format: list of exports
        data = props
        if isinstance(data, list):
            for export in data:
                if isinstance(export, dict):
                    data = export
                    break

        if not isinstance(data, dict):
            return ""

        # Find the row
        row_data = data.get(row_name)
        if isinstance(row_data, dict):
            # Return the first column that has the hex hash pattern
            import re
            for key in row_data:
                if re.match(r'.+_[0-9A-F]{32}$', key):
                    return key
            # Fallback: first key that isn't metadata
            for key in row_data:
                if not key.startswith("_"):
                    return key

        return ""
    except Exception:
        return ""


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

# Internal commands not shown in UI dropdown but supported for round-tripping
_INTERNAL_COMMANDS = {
    "set_dt":     _cmd_set_dt,
    "edit_dt":    _cmd_edit_dt,
}

SIMPLE_COMMANDS = list(COMMAND_MAP.keys())


# ──────────────────────────────────────────────
# Help text for each command
# ──────────────────────────────────────────────

COMMAND_HELP = {
    "set":        "set [params] <object> <property> [DTKey] [Index] <value>\n  Set a property on an object (SparkPatchEntry, Type 1).",
    "set_cmp":    "set_cmp [params] <object> <property> <old_value> <new_value>\n  Set only if current value matches old_value.",
    "clone":      "clone <source_object> <dest_object>\n  Clone an object to a new path.",
    "delete":     "delete <object>\n  Delete/clear an object.",
    "create":     "create <object> <class_name>\n  Create a new object of the given class.",
    "set_array":  "set_array [params] <object> <property> <(elements...)>\n  Set an entire array property.",
    "add":        "add [params] <object> <array_property> <new_element>\n  Add an element to an array.",
    "remove":     "remove [params] <object> <array_property> <element>\n  Remove an element from an array.",
    "set_if":     "set_if [params] <object> <property> <condition> <new_value>\n  Conditionally set a property.",
    "set_struct": "set_struct [params] <object> <struct.field> <value>\n  Set a field within a struct property.",
    "edit":       "edit [params] <object> <property> [DTKey] [Index] <value>\n  Level-specific patch (SparkLevelPatchEntry, Type 1, default MatchAll).",
    "early_set":  "early_set [params] <object> <property> [DTKey] [Index] <value>\n  Early level patch (SparkEarlyLevelPatchEntry).",
    "news":       "news <header>,<image_url>,<article_url>,<body>\n  Inject a news item (InjectNewsItem).",
    "exec":       "exec <filename>\n  Execute/include another mod file.",
    "rename":     "rename <object> <new_name>\n  Rename an object.",
    "merge":      "merge [CharName] <object> <property> <value>\n  Character-loaded patch (SparkCharacterLoadedEntry).",
}