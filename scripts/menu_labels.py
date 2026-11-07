"""The authorized, byte-preserving portfolio navigation label replacement."""

TARGET_HREF = 'https://opengym.jsuisfray.blitz.cloud/'
ORIGINAL_LABELS = ('Sport', 'Training')
NEW_LABEL = 'FrayFit'


def menu_anchor(label):
    return (f'<a class="nav-link" href="{TARGET_HREF}">'
            f'<span class="nav-text">{label}</span></a>').encode('utf-8')


def menu_label_counts(data):
    return {label: data.count(menu_anchor(label))
            for label in (*ORIGINAL_LABELS, NEW_LABEL)
            if menu_anchor(label) in data}


def rename_menu(data):
    for label in ORIGINAL_LABELS:
        data = data.replace(menu_anchor(label), menu_anchor(NEW_LABEL))
    return data
