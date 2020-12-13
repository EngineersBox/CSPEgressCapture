from bs4 import BeautifulSoup
from urllib.parse import urlsplit
from collections import deque
import requests, requests.exceptions, sys, asyncio, uuid

LINE_STRING = "--------------------------------------------------------------------"

class URLState:

    def __init__(self, new_urls=deque([]), processed_urls=set(), local_urls=set(), foreign_urls=set(), broken_urls=set()):
        # a queue of urls to be crawled
        self.new_urls = new_urls
        # a set of urls that we have already crawled
        self.processed_urls = processed_urls
        # a set of domains inside the target website
        self.local_urls = local_urls
        # a set of domains outside the target website
        self.foreign_urls = foreign_urls
        # a set of broken urls
        self.broken_urls = broken_urls

class CrawlerConfig:

    def __init__(self, domain, ofile, limit, mute, asynchronous):
        self.domain = domain
        self.ofile = ofile
        self.limit = limit
        self.mute = mute
        self.asynchronous = asynchronous

class ICrawlerBase:

    def __init__(self, config: CrawlerConfig):
        self.url_state = URLState()
        self.config = config

    def extractResolveLinks(self, response,  url):
        # extract base url to resolve relative links
        parts = urlsplit(url)
        base = "{0.netloc}".format(parts)
        strip_base = base.replace("www.", "")
        base_url = "{0.scheme}://{0.netloc}".format(parts)
        path = url[:url.rfind('/')+1] if '/' in parts.path else url

        # create a beutiful soup for the html document
        soup = BeautifulSoup(response.text, "lxml")

        for link in soup.find_all('a'):
            # extract link url from the anchor
            anchor = link.attrs["href"] if "href" in link.attrs else ''

            if anchor.startswith('/'):
                local_link = base_url + anchor
                self.url_state.local_urls.add(local_link)
            elif strip_base in anchor:
                self.url_state.local_urls.add(anchor)
            elif not anchor.startswith('http'):
                local_link = path + anchor
                self.url_state.local_urls.add(local_link)
            else:
                self.url_state.foreign_urls.add(anchor)

        for i in self.url_state.local_urls:
            if not i in self.url_state.new_urls and not i in self.url_state.processed_urls:
                self.url_state.new_urls.append(i)
        return self.url_state

    def crawlUrlTask(self):
        # a queue of urls to be crawled
        self.url_state = URLState(deque([self.config.domain]))
        # move next url from the queue to the set of processed urls
        url = self.url_state.new_urls.popleft()
        self.url_state.processed_urls.add(url)
        is_broken = False
        # get url's content
        print("Processing %s" % url)
        response = None
        try:
            response = requests.head(url)
        except (requests.exceptions.MissingSchema, requests.exceptions.ConnectionError, requests.exceptions.InvalidURL, requests.exceptions.InvalidSchema):
            # add broken urls to it's own set, then continue
            self.url_state.broken_urls.add(url)
            return self.url_state

        if 'content-type' in response.headers:
            content_type = response.headers['content-type']
            if not 'text/html' in content_type:
                return self.url_state

        try:
            response = requests.get(url)
        except (requests.exceptions.MissingSchema, requests.exceptions.ConnectionError, requests.exceptions.InvalidURL, requests.exceptions.InvalidSchema):
            # add broken urls to it's own set, then continue
            self.url_state.broken_urls.add(url)
            return self.url_state

        # extract base url to resolve relative links
        self.url_state = self.extractResolveLinks(
            self.url_state, response, url)
        return self.url_state

    def reportResults(self):
        if self.config.mute is False:
            if self.config.ofile is not None:
                return report_file(self.config.ofile, self.url_state.processed_urls, self.url_state.local_urls, self.url_state.foreign_urls, self.url_state.broken_urls)
            else:
                return report(self.url_state.processed_urls, self.url_state.local_urls, self.url_state.foreign_urls, self.url_state.broken_urls)
        else:
            if self.config.ofile is not None:
                return mute_report_file(self.config.ofile, self.url_state.local_urls)
            else:
                return mute_report(self.url_state.local_urls)

class AsyncCrawler(ICrawlerBase):

    def __init__(self, config: CrawlerConfig):
        super(self, config)
        self.tasks_url_state = {}

    async def crawl(self):
        task_id = str(uuid.uuid4())
        self.tasks_url_state[task_id] = self.crawlUrlTask(self.config.domain)
        next_urls = self.tasks_url_state[task_id].new_urls
        try:
            results = await asyncio.gather(*(self.crawlUrlTask(next_domain for next_domain in next_urls)))
            for res in results:
                self.tasks_url_state[str(uuid.uuid4())] = res
        except KeyboardInterrupt:
            super.reportResponse()

class Crawler(ICrawlerBase):

    def __init__(self, config: CrawlerConfig):
        super(self, config)

    def crawl(self):
        # a queue of urls to be crawled
        self.url_state.new_urls = deque([self.config.domain])
        try:
            # process urls one by one until we exhaust the queue
            while len(self.url_state.new_urls):
                # move next url from the queue to the set of processed urls
                url = self.url_state.new_urls.popleft()
                res = self.crawlUrlTask(url)
                self.url_state.processed_urls = set(self.url_state.processed_urls.union(res.processed_urls))
                self.url_state.broken_urls = set(self.url_state.processed_urls.union(res.broken_urls))
                self.url_state.new_urls = set(self.url_state.processed_urls.union(res.new_urls))
                self.url_state.foreign_urls = set(self.url_state.processed_urls.union(res.foreign_urls))
                self.url_state.local_urls = set(self.url_state.processed_urls.union(res.local_urls))

            print()
            self.reportResults()
        
        except KeyboardInterrupt:
            self.reportResults()
            sys.exit()

class LimitCrawler(ICrawlerBase):

    def __init__(self, config: CrawlerConfig):
        super(self, config)

    def crawlLimitUrlTask(self):
        # move next url from the queue to the set of processed urls
        url = self.url_state.new_urls.popleft()
        self.url_state.processed_urls.add(url)
        # get url's content
        print("Processing %s" % url)
        try:
            response = requests.get(url)
        except (requests.exceptions.MissingSchema, requests.exceptions.ConnectionError, requests.exceptions.InvalidURL, requests.exceptions.InvalidSchema):
            # add broken urls to it's own set, then continue
            self.url_state.broken_urls.add(url)
            return

        # extract base url to resolve relative links
        parts = urlsplit(url)
        base = "{0.netloc}".format(parts)
        strip_base = base.replace("www.", "")
        base_url = "{0.scheme}://{0.netloc}".format(parts)
        path = url[:url.rfind('/')+1] if '/' in parts.path else url

        # create a beutiful soup for the html document
        soup = BeautifulSoup(response.text, "lxml")

        for link in soup.find_all('a'):
            # extract link url from the anchor
            anchor = link.attrs["href"] if "href" in link.attrs else ''
            print(anchor)

            if self.limit in anchor:
                self.url_state.limit_urls.add(anchor)
            else:
                pass

        for i in self.url_state.limit_urls:
            if not i in self.url_state.new_urls and not i in self.url_state.processed_urls:
                self.url_state.new_urls.append(i)

    def reportLimitResults(self):
        if self.config.mute is False:
            if self.config.ofile is not None:
                return limit_report_file(self.config.limit, self.config.ofile, self.url_state.processed_urls, self.url_state.limit_urls, self.url_state.broken_urls)
            else:
                return limit_report(self.config.limit, self.url_state.processed_urls, self.url_state.limit_urls, self.url_state.broken_urls)
        else:
            if self.config.ofile is not None:
                return limit_mute_report_file(self.config.limit, self.config.ofile, self.url_state.limit_urls)
            else:
                return limit_mute_report(self.config.limit, self.url_state.limit_urls)

    def crawl(self):
        try:
            # process urls one by one until we exhaust the queue
            while len(self.url_state.new_urls):
                self.crawlLimitUrlTask()

            print()
            self.reportLimitResults(self.config.ofile, self.config.mute)

        except KeyboardInterrupt:
            sys.exit()


def limit_report_file(limit, ofile, processed_urls, limit_urls, broken_urls):
    with open(ofile, 'w') as f:
        print(
            LINE_STRING, file=f)
        print("All found URLs:", file=f)
        for i in processed_urls:
            print(i, file=f)
        print(
            LINE_STRING, file=f)
        print("All " + limit + "URLs:", file=f)
        for j in limit_urls:
            print(j, file=f)
        print(
            LINE_STRING, file=f)
        print("All broken URL's:", file=f)
        for z in broken_urls:
            print(z, file=f)


def limit_report(limit, processed_urls, limit_urls, broken_urls):
    print(LINE_STRING)
    print("All found URLs:")
    for i in processed_urls:
        print(i)
    print(LINE_STRING)
    print("All " + limit + " URLs:")
    for j in limit_urls:
        print(j)
    print(LINE_STRING)
    print("All broken URL's:")
    for z in broken_urls:
        print(z)


def limit_mute_report_file(limit, ofile, limit_urls):
    with open(ofile, 'w') as f:
        print(
            LINE_STRING, file=f)
        print("All " + limit + " URLs:", file=f)
        for j in limit_urls:
            print(j, file=f)


def limit_mute_report(limit, limit_urls):
    print(LINE_STRING)
    print("All " + limit + "URLs:")
    for i in limit_urls:
        print(i)

def report_file(ofile, processed_urls, local_urls, foreign_urls, broken_urls):
    with open(ofile, 'w') as f:
        print(
            LINE_STRING, file=f)
        print("All found URLs:", file=f)
        for i in processed_urls:
            print(i, file=f)
        print(
            LINE_STRING, file=f)
        print("All local URLs:", file=f)
        for j in local_urls:
            print(j, file=f)
        print(
            LINE_STRING, file=f)
        print("All foreign URLs:", file=f)
        for x in foreign_urls:
            print(x, file=f)
        print(LINE_STRING, file=f)
        print("All broken URL's:", file=f)
        for z in broken_urls:
            print(z, file=f)


def report(processed_urls, local_urls, foreign_urls, broken_urls):
    print(LINE_STRING)
    print("All found URLs:")
    for i in processed_urls:
        print(i)
    print(LINE_STRING)
    print("All local URLs:")
    for j in local_urls:
        print(j)
    print(LINE_STRING)
    print("All foreign URLs:")
    for x in foreign_urls:
        print(x)
    print(LINE_STRING)
    print("All broken URL's:")
    for z in broken_urls:
        print(z)


def mute_report_file(ofile, local_urls):
    with open(ofile, 'w') as f:
        print(
            LINE_STRING, file=f)
        print("All local URLs:", file=f)
        for j in local_urls:
            print(j, file=f)


def mute_report(local_urls):
    print(LINE_STRING)
    print("All local URLs:")
    for i in local_urls:
        print(i)