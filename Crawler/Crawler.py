import requests
import os
from bs4 import BeautifulSoup
import json
import numpy as np
import pandas
import copy


# 声明一个爬虫类
class Crawler:
    def __init__(self):

        # 将爬虫程序伪装成浏览器发送请求
        self.camouflage = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.81 Safari/537.36 Edg/104.0.1293.54'
        }

    def crawler_IEEE(self):
        """
        爬取一个IEEE-spectrum上的统计数据
        """

        # 保存到对应的文件夹
        data_path = "IEEE"
        if (not os.path.exists(data_path)):
            os.makedirs(data_path)

        # IEEE的官方统计页面
        root_url = "https://spectrum.ieee.org/top-programming-languages-2022"
        # root_text = requests.get(url=root_url, headers=self.camouflage).text

        # 发现该页面是一个html嵌套了另一个html，数据都在嵌套的html中，而直接使用requests.get().text爬取的html中没有包含
        # 内层html的数据，但是浏览器中可以看到
        # 外层的页面可以看到一些分析

        embed_url = "https://flo.uri.sh/visualisation/10817270/embed?auto=1"
        # 这里获得的html包含了所有的数据，但由于没有js等内容，仍与网页上的html源码大不相同
        embed_text = requests.get(url=embed_url, headers=self.camouflage).text
        soup = BeautifulSoup(embed_text, 'lxml')
        with open(os.path.join(data_path, 'raw_data.html'), 'w', encoding='utf-8') as f:
            f.write(embed_text)
        text = soup.select('script')[-1].text
        # 数据都在最后一个script的程序段中的_flourish_data
        # 通过首位定位来截取_flourish_data对应的json
        st = text.find("_Flourish_data ") + len("_Flourish_data =")
        ed = text.find("]}]}") + 4
        # 保存json数据
        with open(os.path.join(data_path, 'data.json'), 'w', encoding='utf-8') as f:
            f.write(text[st:ed])
        # 读取json
        with open(os.path.join(data_path, 'data.json'), 'r', encoding='utf-8') as f:
            root_data = json.load(f)

        # 用于构建DataFrame的字典
        info_dic = {}
        for item in root_data["data"]:
            # print(item["label"])
            # 添加元素到对应的位置
            info_dic.setdefault(item["label"], []).append(
                float(item["value"][0]))
        # print(info_dic)
        info_table = pandas.DataFrame(
            info_dic, index=['Spectrum', 'Jobs', 'Trending'])
        # 进行转置，更直观
        info_table = pandas.DataFrame(
            info_table.T, index=info_table.columns, columns=info_table.index)
        info_table.to_csv(os.path.join(data_path, 'data.csv'))

        print("data from IEEE is stored successfull!\n")

    def crawler_TIOBE(self):
        """
        爬取TIOBE上的数据
        """
        # TIOBE可以常规爬取，不像IEEE数据是调用来的

        # 创建TIOBE的数据来源
        data_path = "TIOBE"
        if (not os.path.exists(data_path)):
            os.makedirs(data_path)

        root_url = "https://www.tiobe.com/tiobe-index/"
        page_text = requests.get(url=root_url, headers=self.camouflage).text
        # with open(os.path.join(data_path, "test.html"), 'w', encoding='utf-8') as f:
        #     f.write(page_text)

        # 使用bs4定位到表格
        soup = BeautifulSoup(page_text, 'lxml')
        root_data = soup.select("tbody > tr")
        # 构建DataFrame的字典
        info_dict = {}
        for i, item in enumerate(root_data):
            # 前20和后30的标签有些许不同
            if i < 20:
                meta_info = item.select('td')
                # 2022年12月的排名
                info_dict.setdefault(meta_info[4].text, []).append(
                    int(meta_info[0].text))
                # 2022年12月所占份额，百分数转为小数，然后再四舍五入到同一位数
                info_dict.setdefault(meta_info[4].text, []).append(
                    np.round(float(meta_info[5].text.strip('%'))/100, 4))
                # 2022年相比2021年的排名变化，正为上升，0为保持，负为下降
                info_dict.setdefault(meta_info[4].text, []).append(
                    (int(meta_info[1].text) - int(meta_info[0].text))
                )

            else:
                meta_info = item.select('td')
                # 排名
                info_dict.setdefault(meta_info[1].text, []).append(
                    int(meta_info[0].text))
                # 份额
                info_dict.setdefault(meta_info[1].text, []).append(
                    np.round(float(meta_info[2].text.strip('%'))/100, 4))
                # 后30名的语言没有排名变化情况，全部是nan
                info_dict.setdefault(meta_info[1].text, []).append(np.NAN)
        info_table = pandas.DataFrame(
            info_dict, index=["Position", "Ratings", "Change"])
        # 进行转置
        info_table = pandas.DataFrame(
            info_table.T, index=info_table.columns, columns=info_table.index)

        info_table.to_csv(os.path.join(data_path, 'data.csv'))

        print("data from TIOBE is stored successfull!\n")

    def crawler_Leetcode(self):
        """
        爬取leetcode 剑指Offer2上题单上所有题目不同语言题解的数量
        """
        # 创建Leetcode的数据来源
        data_path = "Leetcode"
        if (not os.path.exists(data_path)):
            os.makedirs(data_path)

        # 使用get请求的话只会获得第一页的题目，想获得别的页面的内容需要用post获取json
        # url = "https://leetcode.cn/problemset/all/?page=2"

        url = "https://leetcode.cn/graphql/"

        step = 0

        with open(os.path.join(data_path, "problems.txt"), "w", encoding="utf-8") as f:
            while True:

                # post中的参数表，skip表示跳过了几个题目
                para = {"query": "\n    query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {\n  problemsetQuestionList(\n    categorySlug: $categorySlug\n    limit: $limit\n    skip: $skip\n    filters: $filters\n  ) {\n    hasMore\n    total\n    questions {\n      acRate\n      difficulty\n      freqBar\n      frontendQuestionId\n      isFavor\n      paidOnly\n      solutionNum\n      status\n      title\n      titleCn\n      titleSlug\n      topicTags {\n        name\n        nameTranslated\n        id\n        slug\n      }\n      extra {\n        hasVideoSolution\n        topCompanyTags {\n          imgUrl\n          slug\n          numSubscribed\n        }\n      }\n    }\n  }\n}\n    ", "variables": {
                    "categorySlug": "", "skip": 50*step, "limit": 50, "filters": {"orderBy": "SOLUTION_NUM", "sortOrder": "DESCENDING", "listId": "xb9nqhhg"}}}

                resp = requests.post(
                    url=url, headers=self.camouflage, json=para)
                json_data = resp.json()
                json_data = json_data['data']['problemsetQuestionList']['questions']
                if(len(json_data) == 0):
                    break
                for item in json_data:
                    id = item['frontendQuestionId']
                    title = item['titleCn']
                    href = item['titleSlug']
                    f.write(id + "," + title + "," + href + "\n")
                step = step + 1
        print("the problems are stored\n")

        # 一道题的题解的内容还是通过post请求的; 语言的种类也是post爬取的
        solution_url = 'https://leetcode.cn/graphql/'

        # 爬取有哪些语言标签的post参数
        languages = {
            "query": "\n    query languageList {\n  languageList {\n    id\n    name\n  }\n}\n    ", "variables": {}}

        languages_dic = requests.post(
            url=solution_url, headers=self.camouflage, json=languages).json()
        languages_dic = languages_dic['data']['languageList']
        # 要将cpp 标签转为C++，题解标签都是c++
        languages_dic[0]['name'] = 'c++'

        language_pattern = {}
        for item in languages_dic:
            # Leetcode将python和python3分开了，但python并不是严格指明python2
            if item['name'] != 'python3':
                language_pattern[item['name']] = 0

        info_dict = {}  # 用于构造DataFrame的字典
        with open(os.path.join(data_path, "problems.txt"), 'r', encoding='utf-8') as f:
            while True:
                line = f.readline().replace('\n', '')  # 存储的换行也会被读取到
                if not line:
                    break
                info = line.split(',')
                problem_slug = info[-1]
                problem_name = info[0] + ": " + info[1]

                # 获取总的题解数，不是每个题解都有语言标签的，最后标签数目求和会小于总题解数
                sums = {"query": "\n    query solutionCount($questionSlug: String!) {\n  solutionNum(questionSlug: $questionSlug)\n}\n    ", "variables": {
                    "questionSlug": problem_slug}}

                total = requests.post(url=solution_url, headers=self.camouflage, json=sums).json()[
                    'data']['solutionNum']

                languages_statistic = copy.deepcopy(
                    language_pattern)  # 存储所有被统计的编程语言出现的次数

                step = 0
                while(1):
                    # 一道题的题解post请求对应的参数，每次取200个
                    para = {"query": "\n    query questionTopicsList($questionSlug: String!, $skip: Int, $first: Int, $orderBy: SolutionArticleOrderBy, $userInput: String, $tagSlugs: [String!]) {\n  questionSolutionArticles(\n    questionSlug: $questionSlug\n    skip: $skip\n    first: $first\n    orderBy: $orderBy\n    userInput: $userInput\n    tagSlugs: $tagSlugs\n  ) {\n    totalNum\n    edges {\n      node {\n        ipRegion\n        rewardEnabled\n        canEditReward\n        uuid\n        title\n        slug\n        sunk\n        chargeType\n        status\n        identifier\n        canEdit\n        canSee\n        reactionType\n        hasVideo\n        favoriteCount\n        upvoteCount\n        reactionsV2 {\n          count\n          reactionType\n        }\n        tags {\n          name\n          nameTranslated\n          slug\n          tagType\n        }\n        createdAt\n        thumbnail\n        author {\n          username\n          profile {\n            userAvatar\n            userSlug\n            realName\n            reputation\n          }\n        }\n        summary\n        topic {\n          id\n          commentCount\n          viewCount\n          pinned\n        }\n        byLeetcode\n        isMyFavorite\n        isMostPopular\n        isEditorsPick\n        hitCount\n        videosInfo {\n          videoId\n          coverUrl\n          duration\n        }\n      }\n    }\n  }\n}\n    ",
                            "variables": {"questionSlug": problem_slug, "skip": 200*step, "first": 200, "orderBy": "DEFAULT", "userInput": "", "tagSlugs": []}}

                    solution = requests.post(
                        url=solution_url, headers=self.camouflage, json=para).json()

                    tags_position = solution['data']['questionSolutionArticles']['edges']
                    if(len(tags_position) == 0):
                        break
                    for item in tags_position:
                        tags = item['node']['tags']
                        overlap = 0  # 可能同时有python和python3，不能重复计算
                        if 'Python' in tags and 'Python3' in tags:
                            overlap = 1
                        for tag in tags:
                            if(tag['name'] == 'Python3' and not overlap):
                                tag['name'] = 'Python'
                            if(tag['name'] == 'Python3' and overlap):
                                continue
                            # 标签上的单词首字母是大写的，要转为小写
                            index = tag['name'].lower()
                            if index in languages_statistic.keys():
                                languages_statistic[index] += 1
                    # 设置进度条
                    print("\r", end="")
                    print(problem_name + ": {}%: ".format(
                        20000*step//total), "▋" * (100*step // total), end="")
                    step += 1

                print("\r", end="")
                print(problem_name + ": 100%: ", "▋" * 50)
                print()
                languages_statistic['total'] = total  # 总共的题解数量
               # print(languages_statistic)
                values = languages_statistic.values()
                info_dict[problem_name] = languages_statistic.values()

        language_pattern['total'] = 0
        info_table = pandas.DataFrame(
            info_dict, index=language_pattern.keys())

        # 进行转置
        info_table = pandas.DataFrame(
            info_table.T, index=info_table.columns, columns=info_table.index)

        info_table.to_csv(os.path.join(data_path, 'data.csv'))

        print("data from Leetcode is stored successfull!\n")


# leetcode的数据量比较大，运行得比较久接近40分钟
if __name__ == "__main__":
    crawler = Crawler()
    # crawler.crawler_IEEE()
    # crawler.crawler_TIOBE()
    # crawler.crawler_Leetcode()
