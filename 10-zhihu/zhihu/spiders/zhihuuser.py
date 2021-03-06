"""
@author:hp
@project:10-zhihu
@file:zhihuuser.py
@ide:PyCharm
@time:2019/4/28-15:29
"""
import base64
import hmac
import json
import logging
import re
import time
from collections import defaultdict
from copy import deepcopy
from hashlib import sha1
from pprint import pprint
from urllib.parse import quote

import execjs
import scrapy
from PIL import Image
from urllib import parse
from scrapy.http.cookies import CookieJar

from zhihu.custom_settings_spider import custom_settings_for_spider1
from zhihu.items import ZhihuItem


class ZhihuSpider(scrapy.Spider):
    name = 'user'
    custom_settings = custom_settings_for_spider1
    # allowed_domains = ['www.zhihu.com']
    start_urls = ['http://www.zhihu.com/']

    handle_httpstatus_list = [403, 400, 302]

    phone = ''  # 账号
    password = ''  # 密码
    username = ''  # 用户名，用于验证登陆
    # keyword = input('输入搜索的关键词:')

    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36"
    headers = {
        # 'x-zse-83': '3_1.1',
        'Host': 'www.zhihu.com',
        # 'content-type': 'application/x-www-form-urlencoded',
        'Referer': 'https://www.zhihu.com/signin',
        'User-Agent': ua
    }

    # 验证码url
    verify_captcha_url = 'https://www.zhihu.com/api/v3/oauth/captcha?lang=en'

    # 登陆URL
    login_url = 'https://www.zhihu.com/api/v3/oauth/sign_in'

    # 主页
    check_url = "https://www.zhihu.com/notifications"

    # 搜索链接
    # 在搜索页面时需要一个search_hash_id,这个search_hash_id每次都会变实际是在第一次请求搜索结果时生成并返回的,要记录下来才能进行后续的请求。
    search_url = 'https://www.zhihu.com/api/v4/search_v3?t=general&q={0}&correction=1&offset={1}&limit=20'

    # 答案链接 question后面的id 0-5-10
    answer_url = "https://www.zhihu.com/api/v4/questions/{0}/answers?include=data%5B%2A%5D.is_normal%2Cadmin_closed_comment%2Creward_info%2Cis_collapsed%2Cannotation_action%2Cannotation_detail%2Ccollapse_reason%2Cis_sticky%2Ccollapsed_by%2Csuggest_edit%2Ccomment_count%2Ccan_comment%2Ccontent%2Ceditable_content%2Cvoteup_count%2Creshipment_settings%2Ccomment_permission%2Ccreated_time%2Cupdated_time%2Creview_info%2Crelevant_info%2Cquestion%2Cexcerpt%2Crelationship.is_authorized%2Cis_author%2Cvoting%2Cis_thanked%2Cis_nothelp%2Cis_labeled%2Cis_recognized%2Cpaid_info%3Bdata%5B%2A%5D.mark_infos%5B%2A%5D.url%3Bdata%5B%2A%5D.author.follower_count%2Cbadge%5B%2A%5D.topics&limit=5&offset={1}&platform=desktop&sort_by=default"

    # 种子url
    start_user = 'lxb-74'

    # 关注对象
    follows_url = "https://www.zhihu.com/api/v4/members/{user_token}/followees?include=data%5B*%5D.answer_count%2Carticles_count%2Cgender%2Cfollower_count%2Cis_followed%2Cis_following%2Cbadge%5B%3F(type%3Dbest_answerer)%5D.topics&offset=0&limit=20"

    # 关注者 api/v4/
    followers_url = "https://www.zhihu.com/api/v4/members/{user_token}/followers?include={include}&offset={offset}&limit={limit}"
    followers_query = "data%5B*%5D.answer_count%2Carticles_count%2Cgender%2Cfollower_count%2Cis_followed%2Cis_following%2Cbadge%5B%3F(type%3Dbest_answerer)%5D.topics"

    # 查看用户信息
    user_url = "https://www.zhihu.com/api/v4/members/{user_token}?include={include}"
    user_query = 'allow_message,is_followed,is_following,is_org,is_blocking,employments,answer_count,follower_count,articles_count,gender,badge[?(type=best_answerer)].topics'

    # 保存的文件
    cookie_file = "cookie.txt"
    offset = 0
    answer_offset = 0
    answer_offset_dict = defaultdict(int)

    def start_requests(self):
        string = ""
        # 判断是否存在cookie文件若存在则导入
        try:
            with open(self.cookie_file, "r", encoding='utf8') as f:
                string = f.read()
        except:
            logging.warning("文件不存在")

        if string:
            cookies = self.stringToDict(string)
            # cookies = {
            #     'tgw_l7_rout': 'a37704a413efa26cf3f23813004f1a3b',
            #     'capsion_ticket': "2|1:0|10:1556174464|14:capsion_ticket|44:MzQ4M2YzMTIxNmJhNDgwZmJmODhkMzhlMDAzMDYyYTM=|f7d958c6fee8a65adce5db0c606b948c2faab157c41232174e2aff9eac96fc5d",
            #     '_xsrf': 'zKaoOMgqo9Upnh2YE6PwtAPbenI6T0jN',
            #     "z_c0": "2|1:0|10:1556174471|4:z_c0|80:MS4xMG9ud0FnQUFBQUFtQUFBQVlBSlZUWWVrcmwyRkxQY1ZpYkFMTnZCNnA4Q0ZOWm54S200SDRBPT0=|8170556b68a5d7c69ea77b981d346116b41214939d918e0eba293bc8a5324de5"
            # }
            yield scrapy.Request(url=self.check_url, callback=self.after_login, cookies=cookies,
                                 headers=self.headers, meta={'cookiejar': 1})
        else:
            yield scrapy.Request(url=self.verify_captcha_url, headers=self.headers,
                                 callback=self.verify_parse, meta={'cookiejar': 1})  #

    def verify_parse(self, response):
        if "true" in response.text:
            yield scrapy.Request(url=self.verify_captcha_url, headers=self.headers,
                                 callback=self.capture,
                                 method='PUT', meta={'cookiejar': response.meta['cookiejar']})

    def capture(self, response):
        try:
            img_base64 = json.loads(response.body)['img_base64']
        except ValueError:
            logging.warning('获取img_base64的值失败！')

        with open('./captcha.jpg', 'wb') as f:
            f.write(base64.b64decode(img_base64))

        img = Image.open('./captcha.jpg')
        img.show()
        captcha_code = input('请输入图片里的验证码:')

        post_data = {'input_text': captcha_code}
        # Missing argument input_text 和请求头有关 不可携带'x-zse-83': '3_1.1',
        # yield scrapy.Request(url=self.verify_captcha_url, body=json.dumps(post_data),
        #                      callback=self.captcha_login, headers=self.headers, method='POST')
        yield scrapy.FormRequest(
            url=self.verify_captcha_url,
            formdata=post_data,
            callback=self.captcha_login,
            headers=self.headers,
            meta={'cookiejar': response.meta['cookiejar'], "captcha": captcha_code}
        )

    def captcha_login(self, response):
        captcha = response.meta.get("captcha")
        if "true" in response.text:
            logging.info("验证成功")
            # 生成formdata用的参数
            client_id = 'c3cef7c66a1843f8b3a9e6a1e3160e20'
            grant_type = 'password'
            source = 'com.zhihu.web'
            timestamp = str(int(time.time() * 1000))
            signature = self._get_signnature(grant_type, client_id, source, timestamp)
            # 拼接
            text = "client_id=c3cef7c66a1843f8b3a9e6a1e3160e20&grant_type=password&timestamp={0}&" \
                   "source=com.zhihu.web&signature={1}&username=%2B86{2}&password={3}&" \
                   "captcha={4}&lang=en&ref_source=homepage&utm_source=".format(timestamp, signature, self.phone,
                                                                                self.password, captcha)
            with open('./zhihu/get_formdata.js', 'r', encoding='utf-8') as f:
                encry_js = f.read()

            ctx = execjs.compile(encry_js)
            encry = ctx.call('Q', text)
            logging.info("encry:%s", encry)
            # 重配请求头
            login_headers = self.headers.copy()
            # 不加content-type 报错Missing argument grant_type
            login_headers.update({'x-zse-83': '3_1.1', 'content-type': 'application/x-www-form-urlencoded'})

            yield scrapy.Request(
                url=self.login_url,
                method='POST',
                body=encry,
                headers=login_headers,
                callback=self.check_login,
                meta={'cookiejar': response.meta['cookiejar']}
            )

    def check_login(self, response):
        yield scrapy.Request(url=self.check_url, callback=self.after_login, headers=self.headers,
                             meta={'cookiejar': response.meta['cookiejar']}, dont_filter=True)

    def after_login(self, response):
        if self.username in response.text:
            logging.info("登陆成功")
            # 登录成功后，得到要保存的cookies
            Cookies = response.request.headers.getlist('Cookie')
            with open(self.cookie_file, 'w+') as f:
                for cookie in Cookies:
                    f.write(cookie.decode() + '\n')
            # 请求关键词的url
            # search_question = self.search_url.format(quote(self.keyword), self.offset)
            follows_url = self.follows_url.format(user_token=self.start_user)
            followers_url = self.follows_url.format(user_token=self.start_user, include=self.followers_query, offset=0,
                                                    limit=20)

            yield scrapy.Request(url=follows_url, callback=self.parse_follows, headers=self.headers,
                                 meta={'cookiejar': response.meta['cookiejar']})

            # yield scrapy.Request(url=follows_url, callback=self.parse_follows, headers=self.headers,
            #                      meta={'cookiejar': response.meta['cookiejar']})
            # 请求要采集的页面
        else:
            logging.warning("登陆失败")
            yield scrapy.Request(url=self.verify_captcha_url, headers=self.headers, callback=self.verify_parse,
                                 meta={'cookiejar': 1})

    # 解析详情页
    def parse_user(self, response):
        result = json.loads(response.text)
        item = ZhihuItem()

        for field in item.fields:

            if field in result.keys():
                item[field] = result.get(field)
            
        yield item

        # 递归关注
        yield scrapy.Request(self.follows_url.format(user_token=result.get('url_token')), callback=self.parse_follows,
                             meta={'cookiejar': response.meta['cookiejar']})

    def parse_follows(self, response):
        results = json.loads(response.text)

        if 'data' in results.keys():

            for result in results.get('data'):
                yield scrapy.Request(self.user_url.format(user_token=result.get('url_token'), include=self.user_query),
                                     callback=self.parse_user, meta={'cookiejar': response.meta['cookiejar']})

        # 翻页
        if 'paging' in results.keys() and results.get('paging').get('is_end') is False:
            next_page = results.get('paging').get('next').replace('com/members', 'com/api/v4/members')

            yield scrapy.Request(url=next_page, callback=self.parse_follows,
                                 meta={'cookiejar': response.meta['cookiejar']})

    def parse_followers(self, response):
        results = json.loads(response.text)

        if 'data' in results.keys():
            for result in results.get('data'):
                yield scrapy.Request(self.user_url.format(user_token=result.get('url_token'), include=self.user_query),
                                     callback=self.parse_user)

        if 'paging' in results.keys() and results.get('paging').get('is_end') is False:
            next_page = results.get('paging').get('next').replace('com/members', 'com/api/v4/members')

            yield scrapy.Request(next_page, callback=self.parse_followers,
                                 meta={'cookiejar': response.meta['cookiejar']})

    # 处理签名
    def _get_signnature(self, grant_type, client_id, source, timestamp):
        """
        通过 Hmac 算法计算返回签名
        实际是几个固定字符串加时间戳
        :param timestamp: 时间戳
        :return: 签名
        """
        hm = hmac.new(b'd1b964811afb40118a12068ff74a12f4', None, sha1)
        hm.update(str.encode(grant_type))
        hm.update(str.encode(client_id))
        hm.update(str.encode(source))
        hm.update(str.encode(timestamp))
        return str(hm.hexdigest())

    def stringToDict(self, string):
        """
        将从浏览器上Copy来的cookie字符串转化为Scrapy能使用的Dict
        :return:
        tgw_l7_route=a37704a413efa26cf3f23813004f1a3b;
        capsion_ticket="2|1:0|10:1556174464|14:capsion_ticket|44:MzQ4M2YzMTIxNmJhNDgwZmJmODhkMzhlMDAzMDYyYTM=|f7d958c6fee8a65adce5db0c606b948c2faab157c41232174e2aff9eac96fc5d";
        _xsrf=zKaoOMgqo9Upnh2YE6PwtAPbenI6T0jN;
        z_c0="2|1:0|10:1556174471|4:z_c0|80:MS4xMG9ud0FnQUFBQUFtQUFBQVlBSlZUWWVrcmwyRkxQY1ZpYkFMTnZCNnA4Q0ZOWm54S200SDRBPT0=|8170556b68a5d7c69ea77b981d346116b41214939d918e0eba293bc8a5324de5"
        """
        itemDict = {}
        items = string.split(';')

        for item in items:
            num = item.index('=')
            key = item[:num].strip()
            value = item[num + 1:].strip()
            itemDict[key] = value
        return itemDict

    def url2Dict(url):
        res = dict(parse.parse_qsl(url))
        return res
