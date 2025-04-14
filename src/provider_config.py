import os

class ConfigParseError(Exception):
    pass

def parse_entries(filepath, required_keys, entry_id_key, entry_label):
    """
    Parse a config file (provider.txt or models.txt) into a list of dicts, with error reporting.
    - Keys and IDs are case-insensitive.
    - Comments (#) and blank lines ignored.
    - Entries separated by '====' on its own line.
    - Duplicate IDs are reported as errors.
    """
    entries = []
    seen_ids = set()
    entry = {}
    lineno = 0

    def id_key(entry):
        return entry.get(entry_id_key.lower(), "").lower()

    if not os.path.exists(filepath):
        raise ConfigParseError(f"{entry_label} config file '{filepath}' does not exist.")

    with open(filepath, encoding="utf-8") as f:
        for raw_line in f:
            lineno += 1
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line == "====":
                if entry:
                    eid = id_key(entry)
                    if not eid:
                        raise ConfigParseError(
                            f"Missing '{entry_id_key}' in {entry_label} entry at line {lineno}."
                        )
                    if eid in seen_ids:
                        raise ConfigParseError(
                            f"Duplicate {entry_label} '{eid}' found at line {lineno}."
                        )
                    # Check required keys
                    missing = [k for k in required_keys if k not in entry]
                    if missing:
                        raise ConfigParseError(
                            f"Missing keys {missing} in {entry_label} entry at line {lineno}."
                        )
                    entries.append(entry)
                    seen_ids.add(eid)
                    entry = {}
                continue
            # Parse key=value, ignore case
            if "=" in line:
                k, v = line.split("=", 1)
                k = k.strip().lower()
                v = v.strip()
                if k in entry:
                    raise ConfigParseError(
                        f"Duplicate key '{k}' in {entry_label} entry at line {lineno}."
                    )
                entry[k] = v
            else:
                raise ConfigParseError(
                    f"Malformed line in {entry_label} config at line {lineno}: {raw_line}"
                )
    # add last entry if not already added
    if entry:
        eid = id_key(entry)
        if not eid:
            raise ConfigParseError(
                f"Missing '{entry_id_key}' in {entry_label} entry at end of file."
            )
        if eid in seen_ids:
            raise ConfigParseError(
                f"Duplicate {entry_label} '{eid}' at end of file."
            )
        missing = [k for k in required_keys if k not in entry]
        if missing:
            raise ConfigParseError(
                f"Missing keys {missing} in {entry_label} entry at end of file."
            )
        entries.append(entry)
        seen_ids.add(eid)
    return entries

def load_providers(filepath="model/provider.txt"):
    required = ["name", "apikey", "baseurl"]
    return parse_entries(filepath, required, "name", "provider")

def load_models(filepath="model/models.txt"):
    required = ["provider", "model-id"]
    return parse_entries(filepath, required, "model-id", "model")

def get_default_openai_client_and_model():
    """
    Returns a tuple: (openai.AsyncOpenAI client, model_id) using the first provider/model entry.
    Raises ConfigParseError if not found.
    """
    import openai
    providers = load_providers()
    models = load_models()
    if not providers or not models:
        raise ConfigParseError("No providers or models configured.")
    provider = providers[0]
    model = models[0]
    client = openai.AsyncOpenAI(
        api_key=provider["apikey"],
        base_url=provider["baseurl"],
    )
    return client, model["model-id"]