"""Traditional Chinese report text, preserving URLs and HTML attributes."""
import re
from functools import lru_cache
from html.parser import HTMLParser


@lru_cache(maxsize=1)
def _converter():
    try:
        from opencc import OpenCC
    except ImportError:
        from render_common import reexec_in_venv
        reexec_in_venv()
        raise RuntimeError('Traditional Chinese output needs OpenCC. Run: pip install -r requirements.txt')
    return OpenCC('s2t')


def traditional(text):
    if not re.search(r'[\u3400-\u9fff]', text):
        return text
    return _converter().convert(text)


class _TextConverter(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        self.parts.append(self.get_starttag_text())

    def handle_startendtag(self, tag, attrs):
        self.parts.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        self.parts.append(f'</{tag}>')

    def handle_data(self, data):
        self.parts.append(traditional(data))

    def handle_entityref(self, name):
        self.parts.append(f'&{name};')

    def handle_charref(self, name):
        self.parts.append(f'&#{name};')

    def handle_decl(self, decl):
        self.parts.append(f'<!{decl}>')

    def handle_comment(self, data):
        self.parts.append(f'<!--{data}-->')


def traditional_html(html):
    parser = _TextConverter()
    parser.feed(html)
    parser.close()
    return ''.join(parser.parts)
