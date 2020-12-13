from collections import deque

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
