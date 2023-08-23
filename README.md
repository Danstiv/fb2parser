# fb2parser

FB2 parser написанный для проекта [Данные в данные](https://data2data.ru).

Загружен на github для удобства добавления в другие проекты.

Код парсера и этот README может быть изменён или дополнен в будущем.

## Возможности

Поддерживается парсинг в обычный текст и html, а также парсинг с разбивкой на разделы (главы).

## Использование

```
from fb2parser import FB2Parser
with open('document.fb2', 'rb') as document:
    data = document.read()

text = FB2Parser(data).parse()  # Simple text
html = FB2Parser(data).parse(html=True)  # html
text_structure = FB2Parser(data).parse_as_structure()  # list with text chunks
```

**Метод parse и parse_as_structure можно вызывать только 1 раз, повторные вызовы этих методов могут привести к непредсказуемым результатам.**
