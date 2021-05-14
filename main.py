import httpx
from ebooklib import epub
from bs4 import BeautifulSoup
from selenium import webdriver
import re
import time

URL = input('Ranobe url (https://ranobelib.me/{ranobe_name}):\n')

options = webdriver.ChromeOptions()
options.add_argument('--window-size=100,100')
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)
browser = webdriver.Chrome(options=options)
browser.get(f'{URL}?section=chapters')
cover_img_url = BeautifulSoup(browser.page_source, 'lxml').find('div', attrs = {'class': 'media-sidebar__cover'}).img['src']
book_title = BeautifulSoup(browser.page_source, 'lxml').find('div', attrs = {'class': 'media-name__main'}).get_text()
volumes = {}

print('Parsing ranobe nav...')
for i in range(50):
    browser.execute_script(f'window.scrollTo(0, document.body.scrollHeight/50*{i})')
    time.sleep(0.1)
    data = browser.page_source
    soup = BeautifulSoup(data, 'lxml')
    data = soup.find('div', attrs = {'class': 'media-chapters-list'})
    data = data.find_all('div', attrs = {'class': 'media-chapter__body'})
    test = True
    for ob in data:
        title = ob.find('div', attrs = {'class': 'media-chapter__name'}).a.get_text().strip()
        volume = float(title.split(' ')[1])
        chapter = float(title.split(' ')[3])
        temp = volumes[volume] if volume in volumes else {}
        title = title.split('-',1)
        temp = {**temp, chapter: title[1].strip() if len(title) == 2 else ''}
        volumes[volume] = temp
browser.quit()
print('Parsing completed')
print('Volumes:')
for key in volumes.keys():
    print(key)

volume_to_get = float(input('Select volume: '))
vol = volumes[volume_to_get]
print('Chapters:')
for chap in vol:
    print(f'{chap}: {vol[chap]}')

print('Building book...')

book = epub.EpubBook()
client = httpx.Client()
book_spine = []
book_toc = ['nav']

book.set_title(f'{book_title} [{volume_to_get}]')
book.set_language('ru')
book.set_cover(file_name = f'images/cover_img.{cover_img_url.split(".")[-1]}', content = client.get(cover_img_url).content)

for chapter_i in sorted(vol):
    chapter_url = f'{URL}/v{int(volume_to_get) if int(volume_to_get) == volume_to_get else volume_to_get}/c{int(chapter_i) if int(chapter_i) == chapter_i else chapter_i}'
    res = client.get(chapter_url)
    time.sleep(0.1)
    soup = BeautifulSoup(res.content, 'lxml')
    data = soup.find('div', attrs = {'class': 'reader-container'})
    imgs = data.find_all('div', attrs = {'class': 'article-image'})
    data = str(data).replace('<div class="reader-container container container_center">\n','')[:-6]
    name = f'v{int(volume_to_get) if int(volume_to_get) == volume_to_get else volume_to_get}_c{int(chapter_i) if int(chapter_i) == chapter_i else chapter_i}'

    for i, ob in enumerate(imgs):
        img_src = ob.img['data-src']
        img_data = client.get(img_src).content
        ext = img_src.split('.')[-1]
        img_name = f'images/{name}_{i}.{ext}'
        img = epub.EpubItem(file_name = img_name, media_type = 'image/{ext}', content = img_data)
        data = data.replace(str(ob), f'<p><img alt="{img_name}" src="{img_name}"/></p>')
        book.add_item(img)
    data = f'<h2>{vol[chapter_i]}</h2>\n{data}'
    chapter = epub.EpubHtml(title=vol[chapter_i], file_name=f'chap_{name}.xhtml', lang='hr', content=bytes(data, 'utf-8'))
    book.add_item(chapter)
    book_spine.append(chapter)
    book_toc.append( epub.Link(f'chap_{name}.xhtml', f'{int(chapter_i) if int(chapter_i) == chapter_i else chapter_i}.{vol[chapter_i]}', f'chap_{name}') )
    print(f'Ready: {chapter_i}: {vol[chapter_i]}')
print('Building completed')

book.add_item(epub.EpubNcx())
book.add_item(epub.EpubNav())

book.spine = book_spine
book.toc = book_toc

epub.write_epub(f'./results/{book_title} [{volume_to_get}].epub', book)