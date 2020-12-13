class CrawlerConfig:

    def __init__(self, domain, ofile, limit, mute, asynchronous):
        self.domain = domain
        self.ofile = ofile
        self.limit = limit
        self.mute = mute
        self.asynchronous = asynchronous
