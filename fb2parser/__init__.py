import gettext

from bs4 import BeautifulSoup
from bs4.element import NavigableString
from fb2parser.constants import STRING_TAGS, GENRES, MESSAGES


class ParsingError(Exception):

    def __init__(self, error_message):
        self.error_message = error_message

    def get_error(self):
        return self.error_message


class ElementNotFound(ParsingError):

    def __init__(self, element_name):
        super().__init__(('ElementNotFound', {'element_name': element_name}))


class AttributeNotFound(ParsingError):

    def __init__(self, attribute_name):
        super().__init__((
            'AttributeNotFound',
            {'attribute_name': attribute_name},
        ))


class FB2Parser:

    def __init__(self, raw, lang='en'):
        self.soup = BeautifulSoup(raw, 'xml')
        try:
            f = open(f'{__path__[0]}/lang/{lang}.mo', 'rb')
            self._ = gettext.GNUTranslations(f).gettext
            f.close()
        except FileNotFoundError:
            self._ = lambda text: text

    def message_to_text(self, message):
        if isinstance(message, str):
            message = (message)
        if len(message) == 1:
            message = (message[0], {})
        return self._(MESSAGES[message[0]]).format(**message[1])

    def get_genre(self, genre):
        if genre not in GENRES:
            return genre
        return self._(GENRES[genre])

    def _parse(self):
        self.data = {'descriptions': [], 'bodies': []}
        fb = self.soup.find('FictionBook')
        if not fb:
            raise ElementNotFound('FictionBook')
        self.parse_fictionbook(fb)

    def parse(self, html=False):
        self._parse()
        return self.make_text(html)

    def parse_as_structure(self):
        self._parse()
        return self.make_structure()

    def parse_fictionbook(self, fb):
        if not fb.description:
            raise ElementNotFound('description')
        if not fb.body:
            raise ElementNotFound('body')
        for c in fb.children:
            if c.name == 'description':
                self.data['descriptions'].append(self.parse_description(c))
            if c.name == 'body':
                self.data['bodies'].append(self.parse_body(c))

    def parse_description(self, description):
        if not description.find('title-info'):
            raise ElementNotFound('title-info')
        # if not description.find('document-info'):
            # raise ElementNotFound('document-info')
        data = {'title-infos': [], 'src-title-infos': [], 'publish-infos': []}
        for c in description.children:
            if c.name in ['title-info', 'src-title-info']:
                data[c.name.lower() + 's'].append(self.parse_some_title_info(c))
            if c.name == 'publish-info':
                data['publish-infos'].append(self.parse_publish_info(c))
        return data

    def parse_body(self, body):
        # if not body.section:
            # raise ElementNotFound('section')
        result = ''
        structure = []
        html_structure = []
        name = body.get('name')
        if name:
            html_structure.append(['h2', name, None])
            result += name + '\r\n\r\n'
        else:
            html_structure.append(['h2', '---'])
        element = result
        for c in body.children:
            if c.name == 'title':
                t = self.parse_title_as_text(c)
                result += t[0]
                element += t[0]
                html_structure += t[1]
            if c.name == 'epigraph':
                t = self.parse_epigraph_as_text(c)
                result += t[0]
                element += t[0]
                html_structure += t[1]
            if c.name == 'section':
                t = self.parse_section_as_text(c)
                result += ''.join(t[0])
                html_structure += t[1]
                if t[0]:
                    t[0][0] = element + t[0][0]
                    element = ''
                    structure.extend(t[0])
        if element:
            if not structure:
                structure.append('')
            structure[-1] += element
        structure = [i for i in structure if i.strip()]
        return result, structure, html_structure

    def parse_section_as_text(self, section):
        result = []
        html_structure = []
        element = ''
        html_title = '---'
        for c in section.children:
            if c.name == 'title':
                t = self.parse_title_as_text(c)
                element += t[0]
                html_title = t[2]
            if c.name == 'epigraph':
                t = self.parse_epigraph_as_text(c)
                element += t[0]
                html_structure += t[1]
            if c.name == 'annotation':
                t = self.parse_annotation_as_text(c)
                element += t[0]
                html_structure += t[1]
            if c.name == 'section':
                temp = self.parse_section_as_text(c)
                html_structure += temp[1]
                if not temp[0]:
                    temp[0] = ['']
                temp[0][0] = element + temp[0][0]
                element = ''
                result.extend(temp[0])
            if (
                c.name in STRING_TAGS
                or (isinstance(c, NavigableString) and c.strip())
            ):
                t = self.parse_line_as_text(c)
                element += t[0]
                html_structure += t[1]
            if c.name == 'poem':
                t = self.parse_poem_as_text(c)
                element += t[0]
                html_structure += t[1]
            if c.name == 'subtitle':
                t = self.parse_subtitle_as_text(c)
                element += t[0]
                html_structure += t[1]
            if c.name == 'cite':
                t = self.parse_cite_as_text(c)
                element += t[0]
                html_structure += t[1]
            if c.name == 'empty-line':
                t = self.parse_empty_line_as_text(c)
                element += t[0]
                html_structure += t[1]
            if c.name == 'table':
                t = self.parse_table_as_text(c)
                element += t[0]
                html_structure += t[1]
        if not result:
            result.append('')
        result[-1] += element + '\r\n'
        result = [r for r in result if r.strip()]
        if section.get('id', ''):
            first_html_item = ['h3', f'<a name="bunch_{section["id"]}" href="#return_{section["id"]}">{html_title}</a>']
        else:
            first_html_item = ['h3', html_title, None]
        return [result, [first_html_item] + html_structure]

    def parse_some_title_info(self, title_info):
        # if not title_info.genre:
            # raise ElementNotFound('genre')
        # if not title_info.author:
            # raise ElementNotFound('author')
        # if not title_info.find('book-title'):
            # raise ElementNotFound('book-title')
        data = {'genres': [], 'authors': [], 'translators': []}
        for c in title_info.children:
            if c.name == 'genre':
                g = self.parse_genre_as_str(c)
                if g:
                    data['genres'].append(g)
            if c.name == 'author':
                data['authors'].append(self.parse_author_as_text(c))
            if c.name == 'annotation':
                data['annotation'] = self.parse_annotation_as_text(c)
            if c.name == 'translator':
                data['translators'].append(self.parse_translator_as_text(c))
            if c.name == 'sequence':
                data['sequence'] = self.parse_sequence_as_text(c)
            if not c.string:
                continue
            if c.name == 'book-title':
                data['book-title'] = c.string
            if c.name == 'date':
                data['date'] = c.string
            if c.name == 'lang':
                data['lang'] = c.string
            if c.name == 'src-lang':
                data['src-lang'] = c.string
        return data

    def parse_publish_info(self, publish_info):
        result = ''
        html_structure = []
        publisher = publish_info.find('publisher')
        city = publish_info.find('city')
        year = publish_info.find('year')
        sequence = publish_info.find('sequence')
        pub_seq = []
        if publisher and publisher.string:
            pub_seq.append(publisher.string)
        if sequence:
            pub_seq.append(self.parse_sequence_as_text(sequence)[0])
        pub_seq = ', '.join(pub_seq)
        if pub_seq:
            result += pub_seq + '\r\n'
            html_structure.append(['p', pub_seq])
        ci_ye = []
        if city and city.string:
            ci_ye.append(city.string)
        if year and year.string:
            ci_ye.append(year.string)
        ci_ye = ', '.join(ci_ye)
        if ci_ye:
            result += ci_ye + '\r\n'
            html_structure.append(['p', ci_ye])
        return result, html_structure

    def parse_genre_as_str(self, genre):
        match = genre.get('match')
        genre = self.get_genre(genre.string)
        g = genre if not match else f'{genre} ({match}%)'
        return g or None

    def parse_author_as_text(self, author):
        return self.parse_people_as_text(author)

    def parse_translator_as_text(self, translator):
        return self.parse_people_as_text(translator)

    def parse_sequence_as_text(self, sequence):
        if sequence.get('name') is None:
            # raise AttributeNotFound('name')
            return '', [['p', '']]
        result = sequence['name']
        if sequence.get('number'):
            result += f' #{sequence["number"]}'
        return result, [['p', result]]

    def parse_people_as_text(self, p):
        fn = p.find('first-name')
        mn = p.find('middle-name')
        ln = p.find('last-name')
        nn = p.find('nickname')
        hp = p.find('home-page')
        hp = hp.string if hp and hp.string else None
        email = p.find('email')
        email = email.string if email and email.string else None
        full_name_list = []
        if ln and ln.string:
            full_name_list.append(ln.string)
        if fn and fn.string:
            full_name_list.append(fn.string)
        if mn and mn.string:
            full_name_list.append(mn.string)
        if nn and nn.string:
            full_name_list.append('(' + nn.string + ')')
        full_name = ' '.join(full_name_list)
        p = []
        html_structure = []
        if full_name:
            p.append(full_name)
            if hp:
                html_structure.append([None, f'<a href="{hp}">{full_name}</a>'])
            else:
                html_structure.append([None, f'{full_name}'])
        if hp:
            p.append(hp)
            if not full_name:
                html_structure.append([None, f'<a href="{hp}">{hp}</a>'])
        if email:
            p.append(email)
            if html_structure:
                html_structure.append([None, ' '])
                html_structure.append([None, f'(<a mailto="{email}">{email}</a>)'])
            else:
                html_structure.append([None, f'<a mailto="{email}">{email}</a>'])
        p = '\r\n'.join(p)
        return [p, html_structure]

    def parse_annotation_as_text(self, annotation):
        result = ''
        html_structure = []
        for c in annotation.children:
            if c.name in STRING_TAGS or (isinstance(c, NavigableString) and c.strip()):
                t = self.parse_line_as_text(c)
                result += t[0]
                html_structure += t[1]
            if c.name == 'poem':
                t = self.parse_poem_as_text(c)
                result += t[0]
                html_structure += t[1]
            if c.name == 'cite':
                t = self.parse_cite_as_text(c)
                result += t[0]
                html_structure += t[1]
            if c.name == 'subtitle':
                t = self.parse_subtitle_as_text(c)
                result += t[0]
                html_structure += t[1]
            if c.name == 'empty-line':
                t = self.parse_empty_line_as_text(c)
                result += t[0]
                html_structure += t[1]
            if c.name == 'table':
                t = self.parse_table_as_text(c)
                result += t[0]
                html_structure += t[1]
        return result, html_structure

    def get_text(self, element, container='p'):
        if isinstance(element, NavigableString):
            element = str(element)
            return element, [[container, element.strip()]]
        for a in element.find_all('a'):
            for k, v in list(a.attrs.items()):
                if k.endswith('href'):
                    del a[k]
                    if v.startswith('#'):
                        a['name'] = 'return_' + v[1:]
                        v = '#bunch_' + v[1:]
                    a['href'] = v
        return element.get_text(), [[container, element.prettify().strip()]]

    def parse_line_as_text(self, line):
        t = self.get_text(line)
        return t[0] + '\r\n', t[1]

    def parse_empty_line_as_text(self, line):
        return '\r\n', [[None, '<br>']]

    def parse_poem_as_text(self, poem):
        if not poem.stanza:
            return self.get_text(poem)
        result = ''
        html_structure = []
        for c in poem.children:
            if c.name == 'title':
                t = self.parse_title_as_text(c)
                result += t[0]
                html_structure += t[1]
            if c.name == 'epigraph':
                t = self.parse_epigraph_as_text(c)
                result += t[0]
                html_structure += t[1]
            if c.name == 'stanza':
                t = self.parse_stanza_as_text(c)
                result += t[0]
                html_structure += t[1]
            if c.name == 'text-author':
                t = self.parse_text_author_as_text(c)
                result += t[0]
                html_structure += t[1]
            if c.name == 'date':
                t = self.parse_date_as_text(c)
                result += t[0]
                html_structure += t[1]
        return result + '\r\n', html_structure

    def parse_date_as_text(self, date):
        t = self.get_text(date)
        return t[0] + '\r\n', t[1]

    def parse_title_as_text(self, title):
        result = ''
        html_structure = []
        raw_html = ''
        for c in title.children:
            t = None
            if c.name in STRING_TAGS or (isinstance(c, NavigableString) and c.strip()):
                t = self.parse_line_as_text(c)
                result += t[0]
                html_structure += t[1]
            if c.name == 'empty-line':
                t = self.parse_empty_line_as_text(c)
                result += t[0]
                html_structure += t[1]
            if t:
                raw_html += f'<{t[1][0][0]}>{t[1][0][1]}</{t[1][0][0]}>' if t[1][0][0] is not None else t[1][0][1]
        return result + '\r\n', html_structure, raw_html

    def parse_epigraph_as_text(self, epigraph):
        result = ''
        html_structure = []
        for c in epigraph.children:
            if c.name in STRING_TAGS or (isinstance(c, NavigableString) and c.strip()):
                t = self.parse_line_as_text(c)
                result += t[0]
                html_structure += t[1]
            if c.name == 'poem':
                t = self.parse_poem_as_text(c)
                result += t[0]
                html_structure += t[1]
            if c.name == 'cite':
                t = self.parse_cite_as_text(c)
                result += t[0]
                html_structure += t[1]
            if c.name == 'empty-line':
                t = self.parse_empty_line_as_text(c)
                result += t[0]
                html_structure += t[1]
            if c.name == 'text-author':
                t = self.parse_text_author_as_text(c)
                result += t[0]
                html_structure += t[1]
        return result + '\r\n', [[None, '<blockquote>']] + html_structure + [[None, '</blockquote>']]

    def parse_cite_as_text(self, cite):
        result = ''
        html_structure = []
        for c in cite.children:
            if c.name in STRING_TAGS or (isinstance(c, NavigableString) and c.strip()):
                t = self.parse_line_as_text(c)
                result += t[0]
                html_structure += t[1]
            if c.name == 'subtitle':
                t = self.parse_subtitle_as_text(c)
                result += t[0]
                html_structure += t[1]
            if c.name == 'empty-line':
                t = self.parse_empty_line_as_text(c)
                result += t[0]
                html_structure += t[1]
            if c.name == 'poem':
                t = self.parse_poem_as_text(c)
                result += t[0]
                html_structure += t[1]
            if c.name == 'table':
                t = self.parse_table_as_text(c)
                result += t[0]
                html_structure += t[1]
            if c.name == 'text-author':
                t = self.parse_text_author_as_text(c)
                result += t[0]
                html_structure += t[1]
        return result + '\r\n', [[None, '<blockquote>']] + html_structure + [[None, '</blockquote>']]

    def parse_subtitle_as_text(self, subtitle):
        t = self.get_text(subtitle, None)
        if not subtitle.get('id', ''):
            return t[0] + '\r\n', [[None, '<h5>']] + t[1] + [[None, '</h5>']]
        return t[0] + '\r\n', [[None, f'<h5><a name="bunch_{subtitle["id"]}" href="#return_{subtitle["id"]}">']] + t[1] + [[None, '</a></h5>']]

    def parse_table_as_text(self, table):
        if not table.tr:
            raise ElementNotFound('tr')
        tr_list = table.find_all('tr')
        result = ''
        for tr in tr_list:
            result += self.parse_tr_as_text_no_html(tr)
        return result, [[None, table.prettify()]]

    def parse_tr_as_text_no_html(self, tr):
        items = []
        for c in tr.children:
            if c.name == 'th' or c.name == 'td':
                items.append(c.get_text())
        return '\t'.join(items) + '\r\n'

    def parse_text_author_as_text(self, text_author):
        t = self.get_text(text_author)
        return t[0] + '\r\n', t[1]

    def parse_stanza_as_text(self, stanza):
        # if not stanza.v:
            # raise ElementNotFound('v')
        result = ''
        html_structure = []
        for c in stanza.children:
            if c.name == 'title':
                t = self.parse_title_as_text(c)
                result += t[0]
                html_structure += t[1]
            if c.name == 'subtitle':
                t = self.parse_subtitle_as_text(c)
                result += t[0]
                html_structure += t[1]
            if c.name == 'v':
                t = self.parse_v_as_text(c)
                result += t[0]
                html_structure += t[1]
        return '\r\n' + result + '\r\n', html_structure

    def parse_v_as_text(self, v):
        t = self.get_text(v)
        return t[0] + '\r\n', t[1]

    def make_text_from_some_title_info(self, data, set_book_title=False):
        result = ''
        html_structure = []
        if set_book_title:
            self.data['book-title'] = '---'
        if 'book-title' in data:
            if set_book_title:
                self.data['book-title'] = data['book-title']
            result += data['book-title'] + '\r\n'
            html_structure.append(['h1', data['book-title']])
        if 'sequence' in data:
            result += data['sequence'][0] + '\r\n'
            html_structure += data['sequence'][1]
        result += '\r\n'.join(a[0] for a in data['authors']) + '\r\n'
        add = False
        for a in data['authors']:
            if add:
                html_structure.append([None, ', '])
            html_structure += a[1]
            add = True
        html_structure.append([None, '<br/>'])
        if data['translators']:
            temp = self._(MESSAGES['translator'])
            if len(data['translators'])-1:
                temp = self._(MESSAGES['translators'])
            result += temp + ': \r\n' + ('\r\n'.join(t[0] for t in data['translators'])) + '\r\n'
            html_structure.append(['p', temp + ': '])
            add = False
            for t in data['translators']:
                if add:
                    html_structure.append([None, ', '])
                html_structure += t[1]
                add = True
            html_structure.append([None, '<br/>'])
        if data['genres']:
            genres = ', '.join(data['genres'])
            result += '\r\n' + genres + '\r\n'
            html_structure.append(['p', genres])
        if 'lang' in data:
            temp = self._(MESSAGES['language']) + ': '
            result += temp + data['lang'] + '\r\n'
            html_structure.append(['p', temp + data['lang']])
        if 'src-lang' in data:
            temp = self._(MESSAGES['original_language']) + ': '
            result += temp + data['src-lang'] + '\r\n'
            html_structure.append(['p', temp + data['src-lang']])
        if 'date' in data:
            temp = self._(MESSAGES['date']) + ': '
            result += temp + data['date'] + '\r\n'
            html_structure.append(['p', temp + data['date']])
        if 'annotation' in data:
            temp = self._(MESSAGES['annotation'])
            result += temp + ': \r\n' + data['annotation'][0] + '\r\n'
            html_structure.append(['h1', temp])
            html_structure += data['annotation'][1]
        return result, html_structure

    def make_text(self, html=False):
        result = ''
        html_structure = []
        contents_index = 0
        get_book_title = True
        for description in self.data['descriptions']:
            for title_info in description['title-infos']:
                t = self.make_text_from_some_title_info(title_info, get_book_title)
                get_book_title = False
                contents_index += len(t[1])
                result += t[0] + '\r\n'
                html_structure += t[1]
            for src_title_info in description['src-title-infos']:
                t = self.make_text_from_some_title_info(src_title_info)
                temp = self._(MESSAGES['original_metadata'])
                result += temp + ': \r\n' + t[0] + '\r\n'
                contents_index += 1 + len(t[1])
                html_structure.append(['p', temp + ': '])
                html_structure += t[1]
            for publish_info in description['publish-infos']:
                t = publish_info
                temp = self._(MESSAGES['edition_information'])
                result += temp + ': \r\n' + t[0] + '\r\n'
                contents_index += 1 + len(t[1])
                html_structure.append(['p', temp + ': '])
                html_structure += t[1]
        result += '\r\n\r\n'.join([b[0] for b in self.data['bodies']])
        html_structure.append([None, '<hr/>'])
        [html_structure.extend(b[2]) for b in self.data['bodies']]
        if not html:
            return result
        clean_html_structure = []
        section_index = 0
        contents = []
        for html_item in html_structure:
            item = html_item[1]
            if html_item[0] is not None:
                if len(html_item) > 2:
                    if html_item[2] is None:
                        item = f'<{html_item[0]}><a name="section_{section_index}">{html_item[1]}</a></{html_item[0]}>'
                        contents.append((html_item[1].replace('\r', '').replace('\n', ''), f'section_{section_index}'))
                        section_index += 1
                    if html_item[2] == 1:
                        item = f'<{html_item[0]}><a name="return_{html_item[3]}" href="#bunch_{html_item[3]}>{html_item[1]}</a></{html_item[0]}>'
                    if html_item[2] == 2:
                        item = f'<{html_item[0]}><a name="bunch_{html_item[3]}" href="#return_{html_item[3]}>{html_item[1]}</a></{html_item[0]}>'
                else:
                    item = f'<{html_item[0]}>{html_item[1]}</{html_item[0]}>'
            clean_html_structure.append(item)
        contents_html = f'''<h1>{self._(MESSAGES['contents'])}</h1>
<ul style="list-style: none;">
{(chr(13) + chr(10)).join(f'<li><a href="#{item[1]}">{item[0]}</a></li>' for item in contents)}
</ul>'''
        clean_html_structure.insert(contents_index, contents_html)
        return f'''<html>
<head>
<meta charset="UTF-8"/>
<title>{self.data["book-title"]}</title>
</head>
<body>
{(chr(13) + chr(10)).join(clean_html_structure)}
</body>
</html>'''

    def make_structure(self):
        result = ''
        for description in self.data['descriptions']:
            for title_info in description['title-infos']:
                result += self.make_text_from_some_title_info(title_info)[0] + '\r\n'
            for src_title_info in description['src-title-infos']:
                result += self._(MESSAGES['original_metadata']) + ': \r\n' + self.make_text_from_some_title_info(src_title_info)[0] + '\r\n'
            for publish_info in description['publish-infos']:
                result += self._(MESSAGES['edition_information']) + ': \r\n' + publish_info[0] + '\r\n'
        result = [result]
        [result.extend(b[1]) for b in self.data['bodies']]
        return result
