from pyspark.sql import functions as F

RULES = [
    (r"(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}", "<MAC>"),
    (r"\b\d{1,3}(?:\.\d{1,3}){3}\b", "<IP>"),
    (r"0x[0-9a-fA-F]+", "<HEX>"),
    (r"krb5cc_\w+", "krb5cc_<ID>"),
    (r"\bI-x\w+(?:-x\w+)*", "<OBJID>"),
    (r"\b[jk](?=[A-Za-z]*\d)(?=[0-9a-z]*[A-Z])[0-9A-Za-z]{8,}\b", "<QID>"),
    (r"/tmp/tmp\.\w+", "/tmp/tmp.<ID>"),
    (r"\b(?=[0-9]*[a-fA-F])[0-9a-fA-F]{8,}\b", "<HEX>"),
    (r"#\d+#", "<ANON>"),
    (r"\d+", "<N>"),
]

def mask(col):
    for pat, rep in RULES:
        col = F.regexp_replace(col, pat, rep)
    return col
