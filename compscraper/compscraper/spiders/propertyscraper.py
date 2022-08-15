import scrapy
from scrapy.crawler import CrawlerProcess
import json
import gspread
import time
import csv


class PropertyScraper(scrapy.Spider):
    name = 'property'
    start_urls = ['https://www.compass.com/homes-for-sale/detroit-mi-48221/locations=9009/price.min=50K/keywords=tenant/listing-type=mls,fsbo/beds.min=3/property-type=single-family,multi-family/']
    page_number = 40
    all_items = list()
    gc = gspread.service_account(filename="property.json")
    sh = gc.open('property').sheet1


    def parse(self, response):
        items = response.css('div.uc-listingPhotoCard')
        for item in items:
            script_data = item.css(".uc-listingPhotoCard-body + script::text").get()
            try:
                script_json = json.loads(script_data)
            except Exception:
                pass
            url = script_json['url']
            data = {
                'title': ' '.join(item.css('.uc-listingCard-title ::text').getall()),
                'price': item.css('.uc-listingCard-mainStats strong::text').get().replace("$",""),
                'bed': item.css('.uc-listingCard-subStat--beds ::text').get(),
                'bath': item.css('.uc-listingCard-subStat--baths ::text').get(),
                'area(sq.ft.)': item.css('.uc-listingCard-subStat--sqFt ::text').get()

            }

            yield scrapy.Request(url=url, meta={'proerty':data}, callback=self.url_parse)

            if response.css('[data-tn="arrowButtonRight"]'):
             yield scrapy.Request(url=self.start_urls[0]+'start={}/'.format(self.page_number), callback=self.parse)
             self.page_number += 40

    def url_parse(self, response):
        if len(response.css('p.contact-agent-slat__StyledContactInfo-l633vc-10::text')) > 2:
            phone = response.css('p.contact-agent-slat__StyledContactInfo-l633vc-10::text')[1].extract()
        else:
            phone = 'No Data'
        try:
            if len(response.css('p.contact-agent-slat__StyledContactInfo-l633vc-10::text')) > 2:
                mobile = response.css('p.contact-agent-slat__StyledContactInfo-l633vc-10::text')[3].extract()
            else:
                mobile = 'No Data'
        except:
            h=2
        detail_page_data = {
            'name' : response.css('.u-ellipsis::text').get(),
            'email' : response.css('.jOJhnz::text').get(),
            'Phone': phone,
            'Mobile': mobile,
            'year_built' : [v.css(' ::text').extract()[1] for v in response.css(".data-table__TableStyled-ibnf7p-0 > tbody > tr") if v.css(' ::text').extract()[0].lower() == 'Year Built'.lower()][0],
            'lot_size' : [v.css(' ::text').extract()[1] for v in response.css(".data-table__TableStyled-ibnf7p-0 > tbody > tr") if v.css(' ::text').extract()[0].lower() == 'Lot Size'.lower()][0]
        }

        data = response.meta['proerty']
        data.update(detail_page_data)
        self.all_items.append(data)

        # self.all_items.append(detail_page_data)

    def close(spider, reason):
        import pandas as pd
        dataframe = pd.DataFrame(spider.all_items)
        spider.sh.append_row(['Property', 'Price', 'Bed', 'Bath', 'Area','Name', 'Email', 'Phone', 'Mobile','Year Built','Lot Size'])
        row_index = 1
        for data in spider.all_items:
            row_index += 1
            spider.sh.insert_row(list(data.values()), row_index)
            time.sleep(1)



        #dataframe.to_csv('compassData.csv', index=False)


process = CrawlerProcess()
process.crawl(PropertyScraper)
process.start()