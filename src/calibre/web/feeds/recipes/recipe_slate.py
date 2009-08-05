#!/usr/bin/env  python

__license__   = 'GPL v3'
__copyright__ = '2008, Kovid Goyal <kovid at kovidgoyal.net>'
'''
calibre recipe for slate.com
'''

import string, re, sys
from calibre import strftime
from calibre.web.feeds.recipes import BasicNewsRecipe
from calibre.ebooks.BeautifulSoup import BeautifulSoup, NavigableString, CData, Comment, Tag

class PeriodicalNameHere(BasicNewsRecipe):
    # Method variables for customizing downloads
    title                   = 'Slate'
    description             = 'A general-interest publication offering analysis and commentary about politics, news and culture.'
    __author__              = 'GRiker'
    max_articles_per_feed   = 40
    oldest_article          = 7.0
    recursions              = 0
    delay                   = 0
    simultaneous_downloads  = 5
    timeout                 = 120.0
    timefmt                 = ''
    feeds                   = None
    no_stylesheets          = True
    encoding                = None
    language                = _('English')        

    
    
    # Method variables for customizing feed parsing
    summary_length          = 250
    use_embedded_content    = None

    # Method variables for pre/post processing of HTML
    preprocess_regexps = [ (re.compile(r'<p><em>Disclosure: <strong>Slate</strong> is owned by the Washington Post.*</p>', 
                                        re.DOTALL|re.IGNORECASE),
                                        lambda match: ''),
                           (re.compile(r'<p><strong><em>Join the discussion about this story on.*</p>', 
                                        re.DOTALL|re.IGNORECASE),
                                        lambda match: '')   ]

    match_regexps           = []        
    
    # The second entry is for 'Big Money', which comes from a different site, uses different markup
    keep_only_tags          = [dict(attrs={   'id':['article_top', 'article_body']}),
                               dict(attrs={   'id':['content']})  ]
                               
    # The second entry is for 'Big Money', which comes from a different site, uses different markup
    remove_tags             = [dict(attrs={   'id':['toolbox','recommend_tab','insider_ad_wrapper',
                                                    'article_bottom_tools_cntr','fray_article_discussion',
                                                    'fray_article_links','bottom_sponsored_links','author_bio',
                                                    'bizbox_links_bottom','ris_links_wrapper','BOXXLE']}),
                               dict(attrs={    'id':['content-top','service-links-bottom','hed']})   ]
                               
    excludedDescriptionKeywords =   ['Slate V','Twitter feed','podcast']
    excludedTitleKeywords =         ['Gabfest','Slate V','on Twitter']
    excludedAuthorKeywords =        []
    excludedContentKeywords =       ['http://twitter.com/Slate']
            
    extra_css = '.headline      {text-align:left;}\n\
                 .byline        {font-family:   monospace; \
                                 text-align:    left;\
                                 margin-bottom: 0px;}\n\
                 .dateline      {text-align:    left; \
                                 font-size:     smaller;\
                                 height:        0pt;}\n\
                 .imagewrapper  {text-align:    center;}\n\
                 .source        {text-align:    left;}\n\
                 .credit        {text-align:    right;\
                                 font-size:     smaller;}\n\
                 .article_body  {text-align:    left;}\n'
    
    # Local variables to extend class
    baseURL = 'http://slate.com'
    section_dates = []
    
    # class extension methods
    def tag_to_strings(self, tag):
        if not tag:
            return ''
        if isinstance(tag, basestring):
            return tag
        strings = []
        for item in tag.contents:
            if isinstance(item, (NavigableString, CData)):
                strings.append(item.string)
            elif isinstance(item, Tag):
                res = self.tag_to_string(item)
                if res:
                    strings.append(res)
        return strings

    
    def extract_sections(self):
        soup = self.index_to_soup( self.baseURL )
        soup_top_stories = soup.find(True, attrs={'class':'tap2_topic entry-content'})
        soup = soup.find(True, attrs={'id':'toc_links_container'})

        todays_section = soup.find(True, attrs={'class':'todaydateline'})
        self.section_dates.append(self.tag_to_string(todays_section,use_alt=False)) 
        self.section_dates.append(self.tag_to_string(todays_section,use_alt=False)) 
        
        older_section_dates = soup.findAll(True, attrs={'class':'maindateline'})
        for older_section in older_section_dates :
            self.section_dates.append(self.tag_to_string(older_section,use_alt=False))

        headline_stories = soup_top_stories.find('ul')
        section_lists = soup.findAll('ul')
        # Prepend the headlines to the first section
        section_lists[0].insert(0,headline_stories)

        sections = []
        for section in section_lists :
            sections.append(section)
        return sections

            
    def extract_section_articles(self, sections_html) :
        #       Find the containers with section content
        soup = self.index_to_soup(str(sections_html))
        sections = soup.findAll('ul')
        
        articles = {}
        key = None
        ans = []
        
        for (i,section) in enumerate(sections) :
            
            # Get the section name
            if section.has_key('id') :
                key = self.section_dates[i]
                articles[key] = []
                ans.append(key)
            else :
                continue
            
            # Get the section article_list
            article_list = section.findAll('li')
            
            # Extract the article attributes
            for article in article_list :
                bylines = self.tag_to_strings(article)
                url = article.a['href']
                title = bylines[0]
                full_title = self.tag_to_string(article)

                author = None
                description = None
                pubdate = None
                
                if len(bylines) == 2 and self.tag_to_string(article).find("Today's Papers") > 0 :
                    description = "A summary of what's in the major U.S. newspapers."
                
                if len(bylines) == 3 :
                    author = bylines[2].strip()
                    author = re.sub('[\r][\n][\t][\t\t]','', author)
                    author = re.sub(',','', author)
                    if bylines[1] is not None :
                        description = bylines[1]
                        full_byline = self.tag_to_string(article)
                        if full_byline.find('major U.S. newspapers') > 0 :
                            description = "A summary of what's in the major U.S. newspapers."

                if len(bylines) > 3  and author is not None:
                    author += " | "
                    for (i,substring) in enumerate(bylines[3:]) :
                        #print "substring: %s" % substring.encode('cp1252')
                        author += substring.strip()
                        if i < len(bylines[3:]) :
                            author += " | "

                # Skip articles whose descriptions contain excluded keywords
                if description is not None and len(self.excludedDescriptionKeywords):
                    excluded = re.compile('|'.join(self.excludedDescriptionKeywords))
                    found_excluded = excluded.search(description)
                    if found_excluded :
                        if self.verbose : self.log("  >>> skipping %s (description keyword exclusion: %s) <<<\n" % (title, found_excluded.group(0)))
                        continue

                # Skip articles whose title contain excluded keywords
                if full_title is not None and len(self.excludedTitleKeywords):
                    excluded = re.compile('|'.join(self.excludedTitleKeywords))
                    #self.log("evaluating full_title: %s" % full_title)
                    found_excluded = excluded.search(full_title)
                    if found_excluded :
                        if self.verbose : self.log("  >>> skipping %s (title keyword exclusion: %s) <<<\n" % (title, found_excluded.group(0)))
                        continue

                # Skip articles whose author contain excluded keywords
                if author is not None and len(self.excludedAuthorKeywords):
                    excluded = re.compile('|'.join(self.excludedAuthorKeywords))
                    found_excluded = excluded.search(author)
                    if found_excluded :
                        if self.verbose : self.log("  >>> skipping %s (author keyword exclusion: %s) <<<\n" % (title, found_excluded.group(0)))
                        continue

                skip_this_article = False    
                # Check to make sure we're not adding a duplicate
                for article in articles[key] :
                    if article['url'] == url :
                        skip_this_article = True
                        break
                        
                if skip_this_article :
                    continue

                # Build the dictionary entry for this article   
                feed = key
                if not articles.has_key(feed) :
                    articles[feed] = []
                articles[feed].append(dict(title=title, url=url, date=pubdate, description=description,
                                           author=author, content=''))
            # Promote 'newspapers' to top
            for (i,article) in enumerate(articles[feed]) :
                if article['description'] is not None :
                    if article['description'].find('newspapers') > 0 :
                        articles[feed].insert(0,articles[feed].pop(i))
                                        

        ans = [(key, articles[key]) for key in ans if articles.has_key(key)]
        ans = self.remove_duplicates(ans)        
        return ans
    
    def flatten_document(self, ans):
        flat_articles = []
        for (i,section) in enumerate(ans) :
            #self.log("flattening section %s: " % section[0])
            for article in section[1] :
                #self.log("moving %s to flat_articles[]" % article['title'])
                flat_articles.append(article)
        flat_section = ['All Articles', flat_articles]
        flat_ans = [flat_section]            
        return flat_ans
        
    def remove_duplicates(self, ans):
        # Return a stripped ans
        for (i,section) in enumerate(ans) :
            #self.log("section %s: " % section[0])
            for article in section[1] :
                #self.log("\t%s" % article['title'])
                #self.log("\looking for %s" % article['url'])
                for (j,subsequent_section) in enumerate(ans[i+1:]) :
                    for (k,subsequent_article) in enumerate(subsequent_section[1]) :
                        if article['url'] == subsequent_article['url'] :
                            #self.log( "removing %s (%s) from %s" % (subsequent_article['title'], subsequent_article['url'], subsequent_section[0]) )
                            del subsequent_section[1][k]
        return ans

    def print_version(self, url) :
        return url + 'pagenum/all/'

    # Class methods
    def parse_index(self) :
        sections = self.extract_sections()
        section_list = self.extract_section_articles(sections)
        section_list = self.flatten_document(section_list)        
        return section_list
    
    def get_browser(self) :
        return BasicNewsRecipe.get_browser()

    def stripAnchors(self,soup):
        body = soup.find('div',attrs={'id':['article_body','content']})
        if body is not None:
            paras = body.findAll('p')
            if paras is not None:
                for para in paras:
                    aTags = para.findAll('a')
                    if aTags is not None:
                        for a in aTags:
                            if a.img is None:
                                #print repr(a.renderContents())
                                a.replaceWith(a.renderContents().decode('utf-8','replace'))
        return soup

    def preprocess_html(self, soup) :

        # Remove 'grayPlus4.png' images
        imgs = soup.findAll('img')
        if imgs is not None:
            for img in imgs:
                if re.search("grayPlus4.png",str(img)):
                    img.extract()

        # Delete article based upon content keywords
        if len(self.excludedDescriptionKeywords):
            excluded = re.compile('|'.join(self.excludedContentKeywords))
            found_excluded = excluded.search(str(soup))
            if found_excluded :
                return None

        # Articles from www.thebigmoney.com use different tagging for byline, dateline and body
        head = soup.find('head')
        if head.link is not None and re.search('www\.thebigmoney\.com', str(head)):
            byline = soup.find('div',attrs={'id':'byline'})
            if byline is not None:
                byline['class'] = byline['id']
    
            dateline = soup.find('div',attrs={'id':'dateline'})
            if dateline is not None:
                dateline['class'] = dateline['id']
                
            body = soup.find('div',attrs={'id':'content'})
            if body is not None:
                body['class'] = 'article_body'
                
            # Synthesize a department kicker
            h3Tag = Tag(soup,'h3')
            emTag = Tag(soup,'em')
            emTag.insert(0,NavigableString("the big money: Today's business press"))
            h3Tag.insert(0,emTag)
            soup.body.insert(0,h3Tag)
            
        # Strip anchors from HTML                            
        return self.stripAnchors(soup)
        
    def postprocess_html(self, soup, first_fetch) :

        # Fix up dept_kicker as <h3><em>
        dept_kicker = soup.find('div', attrs={'class':'department_kicker'})
        if dept_kicker is not None :
            kicker_strings = self.tag_to_strings(dept_kicker)
            #kicker = kicker_strings[2] + kicker_strings[3]
            kicker = ''.join(kicker_strings[2:])
            kicker = re.sub('\.','',kicker)
            h3Tag = Tag(soup, "h3")
            emTag = Tag(soup, "em")
            emTag.insert(0,NavigableString(kicker))
            h3Tag.insert(0, emTag)
            dept_kicker.replaceWith(h3Tag)

        # Change <h1> to <h2>
        headline = soup.find("h1")
        if headline is not None :
            h2tag = Tag(soup, "h2")
            h2tag['class'] = "headline"
            strs = self.tag_to_strings(headline)
            result = ''
            for (i,substr) in enumerate(strs) :
                result += substr
                if i < len(strs) -1 :
                    result += '<br />'
            h2tag.insert(0, result)
            headline.replaceWith(h2tag)

        # Fix up the concatenated byline and dateline
        byline = soup.find(True,attrs={'class':'byline'})            
        if byline is not None :
            bylineTag = Tag(soup,'div')
            bylineTag['class'] = 'byline'
            #bylineTag['height'] = '0em'
            bylineTag.insert(0,self.tag_to_string(byline))
            byline.replaceWith(bylineTag)
            
        dateline = soup.find(True, attrs={'class':'dateline'})
        if dateline is not None :
            datelineTag = Tag(soup, 'div')
            datelineTag['class'] = 'dateline'
            #datelineTag['margin-top'] = '0em'
            datelineTag.insert(0,self.tag_to_string(dateline))
            dateline.replaceWith(datelineTag)

        # Change captions to italic, add <hr>
        for caption in soup.findAll(True, {'class':'caption'}) :
            if caption is not None:
                emTag = Tag(soup, "em")
                emTag.insert(0, '<br />' + self.tag_to_string(caption))
                hrTag = Tag(soup, 'hr')
                emTag.insert(1, hrTag)
                caption.replaceWith(emTag)
                
        # Fix photos
        for photo in soup.findAll('span',attrs={'class':'imagewrapper'}):
            if photo.a is not None and photo.a.img is not None:
                divTag = Tag(soup,'div')
                divTag['class'] ='imagewrapper'
                divTag.insert(0,photo.a.img)
                photo.replaceWith(divTag)
        
        return soup
        
    def postprocess_book(self, oeb, opts, log) :

        def extract_byline(href) :
            soup = BeautifulSoup(str(oeb.manifest.hrefs[href]))            
            byline = soup.find(True,attrs={'class':'byline'})            
            if byline is not None:            
                return self.tag_to_string(byline,use_alt=False)
            else :
                return None    
        
        def extract_description(href) :
            soup = BeautifulSoup(str(oeb.manifest.hrefs[href]))
            paragraphs = soup.findAll('p')
            for p in paragraphs :
                if self.tag_to_string(p,use_alt=False).startswith('By ') or \
                   self.tag_to_string(p,use_alt=False).startswith('Posted '):
                    continue                
                comment = p.find(text=lambda text:isinstance(text, Comment))
                if comment is not None:
                    continue
                else:
                    return self.tag_to_string(p,use_alt=False)[:self.summary_length] + '...'
                    
            return None
                                 
        # Method entry point here
        # Single section toc looks different than multi-section tocs
        if oeb.toc.depth() == 2 :
            for article in oeb.toc :
                if article.author is None :
                    article.author = extract_byline(article.href)
                if article.description is None :
                    article.description = extract_description(article.href)
        elif oeb.toc.depth() == 3 :
            for section in oeb.toc :
                for article in section :
                    if article.author is None :
                        article.author = extract_byline(article.href)
                    if article.description is None :
                        article.description = extract_description(article.href)
        
    