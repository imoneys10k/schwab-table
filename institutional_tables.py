"""Source-calibrated, flowing report templates. The spec contains the data.

Column keys map to row.values (ticker/name/sector also accept row metadata).
Rows retain input order; adjacent group labels create institutional group rows.
No template fetches prices, invents portfolio totals, or changes numeric values.
"""
import json
import math
from html import escape

from fonts import font_face_css
from localization import traditional_html

STYLES = ('schwab', 'morgan', 'blackstone', 'ibkr')
CJK = '"Noto Sans CJK TC","Source Han Sans TC","PingFang TC","Microsoft JhengHei",sans-serif'
STACKS = {
    'morgan': f'"MSGloriolaIIStd","Source Sans 3",Arial,{CJK}',
    'blackstone': f'"Trebuchet MS","Source Sans 3",Arial,{CJK}',
    'ibkr': f'"Droid Sans",Arial,{CJK}',
}


def label(value, lang):
    if isinstance(value, dict):
        return str(value.get(lang, value.get('en', '')))
    return '' if value is None else str(value)


def validate(spec, style):
    columns = spec.get('columns', [])
    if not columns or any(not c.get('key') for c in columns):
        raise ValueError(f'{style} needs columns with explicit keys and labels; see examples/{style}_spec.json')
    keys = [c['key'] for c in columns]
    if len(set(keys)) != len(keys):
        raise ValueError('column keys must be unique')
    for col in columns:
        if col.get('format', 'text') not in ('text', 'pct', 'money', 'raw'):
            raise ValueError(f'unsupported format for {col["key"]}')
        if col.get('width', 1) <= 0:
            raise ValueError('column widths must be positive')
    if style == 'blackstone' and len(columns) != 3:
        raise ValueError('Blackstone uses a name column and two period columns')
    if style == 'morgan':
        groups = spec.get('column_groups', [])
        grouped = [k for group in groups for k in group['keys']]
        if len(groups) != 2 or grouped != keys[1:]:
            raise ValueError('Morgan uses two ordered column_groups covering all columns after the name')
    for row in spec.get('rows', []):
        for col in columns:
            value = row.get('values', {}).get(col['key'], row.get(col['key']))
            if value is not None and col.get('format') in ('pct', 'money'):
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise ValueError(f'{col["key"]} must be a finite number or null')
    return columns


def cell_value(row, col):
    return row.get('values', {}).get(col['key'], row.get(col['key']))


def formatted(value, col, lang, style):
    if value is None:
        return 'NA'
    kind = col.get('format', 'text')
    if kind not in ('pct', 'money'):
        return escape(label(value, lang))
    number = format(abs(value), '.1f' if kind == 'pct' else ',.2f')
    if value < 0:
        number = f'({number})' if style == 'blackstone' else '-' + number
    if style == 'blackstone' and kind == 'pct':
        number += '%'
    return number


def headers(spec, columns, lang, style):
    def heading(col):
        return escape(label(col.get('label', col['key']), lang)).replace('\n', '<br>')
    if style != 'morgan':
        return '<tr>' + ''.join(f'<th class="{c.get("align", "left" if c.get("format", "text")=="text" else "right")}">{heading(c)}</th>' for c in columns) + '</tr>'
    upper = f'<tr class="upper"><th rowspan="2" class="left">{heading(columns[0])}</th>'
    upper += ''.join(f'<th colspan="{len(g["keys"])}">{escape(label(g["label"], lang)).replace(chr(10), "<br>")}</th>' for g in spec['column_groups']) + '</tr>'
    lower = '<tr class="lower">' + ''.join(f'<th>{heading(c)}</th>' for c in columns[1:]) + '</tr>'
    return upper + lower


def body_rows(rows, columns, lang, style):
    result = []; previous_group = None
    for row in rows:
        group = label(row.get('group'), lang)
        if group and group != previous_group:
            if style == 'morgan':
                result.append(f'<tr class="group"><th>{escape(group)}</th>'+ '<td></td>'*(len(columns)-1)+'</tr>')
            else:
                result.append(f'<tr class="group"><th colspan="{len(columns)}">{escape(group)}</th></tr>')
        previous_group = group
        cells = []
        for col in columns:
            value = cell_value(row, col)
            align = col.get('align', 'left' if col.get('format', 'text') == 'text' else 'right')
            text = formatted(value, col, lang, style)
            if col['key'] == 'name' and style != 'ibkr' and row.get('ticker') and not row.get('bench'):
                text += ' (' + escape(row['ticker']) + ')'
            if col['key'] == 'name' and style == 'morgan':
                level = row.get('level', 1)
                if not isinstance(level, int) or not 0 <= level <= 2:
                    raise ValueError('Morgan row.level must be 0, 1 or 2')
                align += f' indent{level}'
            raw = escape(json.dumps(value, ensure_ascii=False), quote=True)
            cells.append(f'<td class="{align}" data-key="{escape(col["key"], quote=True)}" data-value="{raw}">{text}</td>')
        result.append(f'<tr class="{"bench" if row.get("bench") else ""}" data-symbol="{escape(row.get("ticker", ""), quote=True)}">' + ''.join(cells) + '</tr>')
    return ''.join(result)


def table(spec, lang, style):
    columns = validate(spec, style)
    widths = ''.join(f'<col style="width:{c.get("width", 100/len(columns))}%">' for c in columns)
    return '<table><colgroup>' + widths + '</colgroup><thead>' + headers(spec, columns, lang, style) + '</thead><tbody>' + body_rows(spec['rows'], columns, lang, style) + '</tbody></table>'


CSS = {
    'morgan': '''#wrap{width:576px;padding:18px}h1{font-size:11px;font-weight:600;margin:0 0 5px}table{font-size:7.875px;line-height:1.05}th,td{padding:2.6px .75px}thead th{text-align:center;font-weight:500;vertical-align:bottom}.upper th{color:#00a1e2;padding-bottom:4px}.upper th:first-child{color:#000}.lower th{padding-bottom:2px}thead{border-bottom:.75px solid #93959b}tbody{border-bottom:.75px solid #93959b}td:not(:first-child){text-align:center}.group th{text-align:left;color:#005aa4;font-weight:500;padding:3px .75px}.group th,.group td{border-top:.75px solid #93959b}.group:first-child th,.group:first-child td{border-top:0}.indent0{padding-left:.75px}.indent1{padding-left:15.8px;color:#00a1e2}.indent2{padding-left:31.55px}tbody td:first-child,.group th{border-right:.75px solid #93959b}.foot{font-size:7.99px;color:#6d6d6d;margin-top:10px;line-height:1.18}''',
    'blackstone': '''#wrap{width:304px;padding:18px}h1{font-family:Georgia,"Times New Roman","Songti TC","Noto Serif CJK TC",serif;font-size:14.04px;font-weight:700;margin:0 0 5px}.subtitle{font-size:9.96px;margin:0 0 29px}table{font-size:9.6px;line-height:1.14}thead th{background:#000;color:#fff;font-weight:700;text-align:center;height:17.92px;padding:0 4px}td{padding:3px 4px;height:17.02px}td:not(:first-child){text-align:center}td:first-child{padding-left:17.92px}.group th{background:#eee;padding:2.5px 10px;text-align:left;height:16.15px;font-weight:700}.group:not(:first-child) th{border-top:7.3px solid #fff}.foot{font-size:8.04px;color:#333;margin-top:18px;line-height:1.2;border-top:.72px solid #000;padding-top:4px}''',
    'ibkr': '''#wrap{width:792px;padding:24px}.report-head{display:flex;align-items:baseline;justify-content:space-between;border-bottom:1px solid #e7e7e7;margin-bottom:16px;padding-bottom:5px}h1{font-size:11px;color:#778899;font-weight:400;margin:0}.date{font-size:7px;color:#778899}h2{font-size:11px;color:#778899;font-weight:400;margin:0 0 6px;padding-left:5px}table{font-size:6px;line-height:1.08}thead th{font-weight:400;vertical-align:bottom;height:16px;padding:0 5px 4px;border-bottom:2px solid #e7e7e7}td{padding:2px;min-height:10px;border-bottom:.5px solid #e7e7e7}th,td{overflow-wrap:anywhere}.exposure{border-top:1px solid #e7e7e7;margin-top:14px;padding-top:18px}.exposure-grid{display:grid;grid-template-columns:1fr 1fr;gap:48px}.foot{font-size:6px;color:#6b6b6b;line-height:1.4;margin-top:28px;padding-top:6px;border-top:1px solid #e7e7e7}.group th{text-align:left;font-weight:400;padding:3px 2px}''',
}


def build_html(spec, lang, style, theme='light'):
    if theme != 'light':
        raise ValueError('Institutional templates use white paper. Dark theme is available with style=schwab.')
    L = spec['langs'][lang]
    main_table = table(spec, lang, style)
    title = escape(L['title'])
    if style == 'ibkr':
        top = f'<div class="report-head"><h1>{title}</h1><span class="date">{escape(label(spec.get("as_of"), lang))}</span></div><h2>{escape(L.get("section", ""))}</h2>'
    else:
        top = f'<h1>{title}</h1>'
        if L.get('subtitle'):
            top += f'<p class="subtitle">{escape(L["subtitle"])}</p>'
    exposure = ''
    if style == 'ibkr' and spec.get('exposure'):
        parts = []
        for block in spec['exposure']:
            parts.append('<div>' + table(block, lang, 'ibkr') + '</div>')
        exposure = f'<section class="exposure"><h2>{escape(L.get("exposure_title", "Exposure"))}</h2><div class="exposure-grid">' + ''.join(parts) + '</div></section>'
    # A rule separates Morgan's two metric groups in the original matrix.
    extra = ''
    if style == 'morgan':
        boundary = 2 + len(spec['column_groups'][0]['keys'])
        extra = f'tbody td:nth-child({boundary}){{border-left:.75px solid #93959b}}'
    html = f'''<!doctype html><html lang="{'zh-Hant' if lang=='zh' else 'en'}"><head><meta charset="utf-8"><title>{title}</title><style>
{font_face_css(style)}
*{{box-sizing:border-box}}body{{margin:0;background:#fff;color:#000;font-family:{STACKS[style]};-webkit-font-smoothing:antialiased}}#wrap{{background:white}}table{{width:100%;border-collapse:collapse;table-layout:fixed}}.left{{text-align:left;overflow-wrap:anywhere}}.right{{text-align:right}}.bench td{{font-weight:600}}{CSS[style]}{extra}
</style></head><body><div id="wrap" data-style="{style}">{top}{main_table}{exposure}<div class="foot">{L.get('foot','')}</div></div></body></html>'''
    return traditional_html(html) if lang == 'zh' else html
