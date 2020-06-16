import typing

import scrapy
import html2markdown


DATABASE_KEY = 'database'
YEAR_KEY = 'year'
NAME_KEY = 'name'
URL_KEY = 'url'


class Austlii(scrapy.Spider):
    name = "austlii"
    start_urls = [
        "http://www8.austlii.edu.au/databases.html"
    ]

    def parse(
        self, response: scrapy.http.Response
    ) -> typing.Generator[scrapy.Request, None, None]:
        """Find all the databases."""
        for db_url in response.xpath('//div[@class="card"]/ul/li'):
            relative_url = db_url.xpath("./a/@href").extract()
            if not relative_url:
                continue
            url = response.urljoin(relative_url[0])
            text = db_url.xpath("./a/text()").extract()[0]
            yield scrapy.Request(
                url=url,
                callback=self.parse_database,
                meta={
                    DATABASE_KEY: text,
                },
                dont_filter=True,
            )

    def parse_database(self, response: scrapy.http.Response) -> typing.Generator[scrapy.Request, None, None]:
        """Find all the years in each database."""
        for year_url in response.xpath('//div[@class="year-specific-options year-options"]/ul/li/h5'):
            url = response.urljoin(year_url.xpath("./a/@href").extract()[0])
            text = year_url.xpath("./a/text()").extract()[0]
            yield scrapy.Request(
                url=url,
                callback=self.parse_years,
                meta={
                    DATABASE_KEY: response.meta[DATABASE_KEY],
                    YEAR_KEY: text,
                },
                dont_filter=True,
            )

    def parse_years(self, response: scrapy.http.Response) -> typing.Generator[scrapy.Request, None, None]:
        """Find all the cases in each year."""
        for case_url in response.xpath('//div[@class="card"]/ul/li'):
            url = response.urljoin(case_url.xpath("./a/@href").extract()[0])
            text = case_url.xpath("./a/text()").extract()[0]
            if url.endswith(".pdf"):
                yield {
                    DATABASE_KEY: response.meta[DATABASE_KEY],
                    YEAR_KEY: response.meta[YEAR_KEY],
                    NAME_KEY: text,
                    URL_KEY: response.url
                }
            else:
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_case,
                    meta={
                        DATABASE_KEY: response.meta[DATABASE_KEY],
                        YEAR_KEY: response.meta[YEAR_KEY],
                        NAME_KEY: text,
                    }
                )

    def parse_case(self, response: scrapy.http.Response) -> typing.Generator[scrapy.Request, None, None]:
        """Download each case."""
        document = response.xpath('//article[@class="the-document"]')
        yield {
            'text': document.xpath("string(.)").extract(),
            DATABASE_KEY: response.meta[DATABASE_KEY],
            YEAR_KEY: response.meta[YEAR_KEY],
            NAME_KEY: response.meta[NAME_KEY],
            URL_KEY: response.url,
        }
