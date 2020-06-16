import typing
import re
from io import BytesIO

import scrapy
import pdftotext
from dateutil.parser import *


CASE_NAME = 'caseName'
CASE_NUMBER = 'caseNumber'
ENTITY_NAME = 'entityName'
ENTITY_CLASS = 'entityClass'
DOCUMENT_NAME = 'documentName'
DATE = 'date'


class HCourt(scrapy.Spider):
    name = "hcourt"
    start_urls = [
        "https://www.hcourt.gov.au/cases/cases-heard"
    ]
    allowed_domains = [
        "hcourt.gov.au"
    ]

    def parse(
        self, response: scrapy.http.Response
    ) -> typing.Generator[scrapy.Request, None, None]:
        """Find all the cases."""
        for case_url in response.xpath('//table[@class="cases"]/tbody/tr/td/a/@href'):
            url = response.urljoin(case_url.extract())
            yield scrapy.Request(
                url=url,
                callback=self.parse_case,
                dont_filter=True,
            )

    def parse_case(
        self, response: scrapy.http.Response
    ) -> typing.Generator[scrapy.Request, None, None]:
        """Find all the documents in the case."""
        item_full_text_div = response.xpath('//div[@class="itemFullText"]')[0]
        case_name = item_full_text_div.xpath('./h2/text()')[0].extract().strip()
        case_number = response.xpath('//h1[@class="itemTitle"]/text()')[0].extract().strip()
        for paragraph in item_full_text_div.xpath('./p'):
            paragraph_text = paragraph.xpath('string(.)').extract()[0]
            link = paragraph.xpath('./a')
            if not link:
                continue
            document_url = link[-1].xpath('./@href')[0]
            url = response.urljoin(document_url.extract())
            date = paragraph_text.split()[0]
            try:
                parse(date)
            except:
                continue
            entity_name = ''
            entity_class = ''
            braces = re.findall(r"\(.*?\)", paragraph_text)
            if braces:
                brace_text = braces[0].replace("(", "").replace(")", "")
                braces_split = [x.strip() for x in brace_text.split("-")]
                entity_name = braces_split[-1]
                if len(braces_split) > 1:
                    entity_class = braces_split[0]
            document_name = link[-1].xpath('./text()').extract()
            yield scrapy.Request(
                url=url,
                callback=self.parse_document,
                meta={
                    CASE_NAME: case_name,
                    CASE_NUMBER: case_number,
                    ENTITY_NAME: entity_name,
                    ENTITY_CLASS: entity_class,
                    DOCUMENT_NAME: document_name,
                    DATE: date,
                },
            )

    def parse_document(
        self, response: scrapy.http.Response
    ) -> typing.Generator[scrapy.Request, None, None]:
        """Parse the document from a case."""
        if not isinstance(response, scrapy.http.TextResponse):
            pdf = pdftotext.PDF(BytesIO(response.body))
            text = "\n\n".join(pdf)
            yield {
                'text': text,
                'url': response.url,
                CASE_NAME: response.meta[CASE_NAME],
                CASE_NUMBER: response.meta[CASE_NUMBER],
                ENTITY_NAME: response.meta[ENTITY_NAME],
                ENTITY_CLASS: response.meta[ENTITY_CLASS],
                DOCUMENT_NAME: response.meta[DOCUMENT_NAME],
                DATE: response.meta[DATE],
            }
