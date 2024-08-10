import nonebot
import requests
from nonebot import on_command, get_driver, logger, on_regex, on_startswith, permission, require, logger
from nonebot.adapters.onebot.v11 import Message, Event, Bot, MessageSegment
from nonebot.adapters.onebot.v11.event import GroupMessageEvent, PrivateMessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.permission import SUPERUSER
import json
import os
import re
from nonebot import on_startswith, on_regex, permission


scheduler = require('nonebot_plugin_apscheduler').scheduler





# 定义文件路径
SUBSCRIPTION_FILE = './data/githubstar/github_subscriptions.json'
# 创建文件路径（如果不存在）
if not os.path.exists('./data/githubstar/'):
    os.makedirs('./data/githubstar/')

# 读取订阅项目
def load_subscriptions():
    if os.path.exists(SUBSCRIPTION_FILE):
        with open(SUBSCRIPTION_FILE, 'r') as f:
            return json.load(f)
    return []


# 保存订阅项目
def save_subscriptions(subscriptions):
    with open(SUBSCRIPTION_FILE, 'w') as f:
        json.dump(subscriptions, f)

# 初始化一个空字典
LAST_DATA_FILE = './data/githubstar/last_data.json'

def save_last_data():
    with open(LAST_DATA_FILE, 'w') as file:
        json.dump(last_data, file)

def load_last_data():
    global last_data
    try:
        with open(LAST_DATA_FILE, 'r') as file:
            last_data = json.load(file)
    except FileNotFoundError:
        # 如果文件不存在，初始化一个空字典
        last_data = {}

def check_github_info():
    # 在这里更新 last_data 字典的内容
    last_data['key'] = 'value'
    save_last_data()

# 在程序启动时加载之前保存的数据
load_last_data()

# 调用函数检查 GitHub 信息
check_github_info()


add_github_subscription = on_regex(
    r"^((添加|增加)(github|GitHub|)(订阅)(.*)(github.com))", priority=1
)



# 添加 GitHub 订阅
@add_github_subscription.handle()
async def add_github_subscription(bot: Bot, event: Event) -> None:
    bot = nonebot.get_bot()
    bot_name = str(bot.config.nickname)
    nickname = bot_name.replace("{", "").replace("}", "").replace("'", "")
    get_project_message = str(event.get_message())
    get_project_name = r"https://github.com/(.+)"
    project_name = re.search(get_project_name, get_project_message)
    if project_name:
        project_name = project_name.group(1)
    else:
        project_name = "未匹配到项目名称"
    get_project_url = r"[a-zA-z]+:\/\/[^\s]*"
    project_url = re.search(get_project_url, get_project_message)
    if project_url:
        project_url = project_url.group(0)
    else:
        project_url = "未匹配到项目地址"
    subscriptions = load_subscriptions()
    #  判断消息来源
    try:
        if event.group_id:
            source = "Group"
    except:
        source = "Private"
    ID = event.group_id if source == "Group" else event.user_id

    # 查找是否已存在该来源的数据
    existing_data = None
    for sub_data in subscriptions:
        if sub_data["source"] == source and sub_data["ID"] == ID:
            existing_data = sub_data
            break

    if existing_data and existing_data["source"] == source and existing_data["ID"] == ID:
        existing_projects = [sub["project_name"] for sub in existing_data["subscription"]]
        if project_name in existing_projects:
            await bot.send(event, f"您已经订阅过[{project_name}]({project_url})了哦~")
            return
        if existing_data["subscription"]:
            code = max([sub["code"] for sub in existing_data["subscription"]]) + 1
        else:
            code = 1
        existing_data["subscription"].append({"code": code, "project_name": project_name, "project_url": project_url})
    else:
        code = 1
        new_data = {"source": source, "ID": ID, "push_enabled": True, "subscription": [{"code": code, "project_name": project_name, "project_url": project_url}]}
        subscriptions.append(new_data)

    save_subscriptions(subscriptions)

    await bot.send(event, f"好的呢~{nickname}已经添加了对[{project_name}]({project_url})的订阅~")




remove_github_subscription = on_regex(
    r"^(删除(github|GitHub|)(订阅)(.*))", priority=1
)

@remove_github_subscription.handle()
async def remove_github_subscription(bot: Bot, event: Event):
    bot = nonebot.get_bot()
    bot_name = str(bot.config.nickname)
    nickname = bot_name.replace("{", "").replace("}", "").replace("'", "")
    project_name = str(event.get_plaintext()).strip()
    remove_project_name = re.sub(r'\[.*?\]', '', re.sub(r'[\u4e00-\u9fa5\s]', '', project_name))
    if remove_project_name == '':
        await bot.send(event, f"删除订阅项目请以”删除订阅 [项目编号|名称|地址]“格式发送即可，[项目编号|名称|地址]可任选其一~")
        return

    if isinstance(event, PrivateMessageEvent):
        source = "Private"
        ID = event.user_id
    else:
        source = "Group"
        ID = event.group_id

    subscriptions = load_subscriptions()
    await bot.send(event, f"{subscriptions}")

    # 检查源和ID是否在JSON中存在
    for sub in subscriptions:
        if sub.get("source") == source and sub.get("ID") == ID:
            for index, sub_info in enumerate(sub.get("subscription")):
                if remove_project_name == str(sub_info.get("code")) or remove_project_name in sub_info.get("project_name") or remove_project_name in sub_info.get("project_url") or remove_project_name in sub_info.get("project_name") + " " + sub_info.get("project_url"):
                    sub.get("subscription").remove(sub_info)
                    await bot.send(event, f"好的呢~{nickname}已经删除了对[{sub_info.get('project_name')}]的订阅~")

                    # 更新订阅信息的编号
                    for i, s in enumerate(sub.get("subscription")):
                        s["code"] = i + 1

                    # 如果订阅列表为空，则清除该用户的订阅信息
                    if not sub.get("subscription"):
                        subscriptions.remove(sub)

                    # 保存订阅信息
                    save_subscriptions(subscriptions)
                    return

            await bot.send(event, f"抱歉，{nickname}没有找到关于[{remove_project_name}]的订阅项目，你可以发送查看订阅来查询目前已订阅的项目再进行删除哦~")
            return

    await bot.send(event, f"抱歉，{nickname}当前并未进行项目订阅，无法删除~")




view_subscription = on_command('查看订阅',aliases={'查询订阅', '订阅详情', '订阅列表'})


@view_subscription.handle()
async def handle_view_subscription(bot: Bot, event: Event):
    subscriptions = load_subscriptions()

    if not subscriptions:
        await bot.send(event, "当前无订阅项目")
        return

    sender_id = event.user_id
    if isinstance(event, PrivateMessageEvent):
        source = "Private"
        ID = event.user_id
    else:
        source = "Group"
        ID = event.group_id

    # 查找对应消息来源和ID的订阅信息
    for subscription_info in subscriptions:
        if subscription_info["source"] == source and subscription_info["ID"] == ID:
            subscription_data = subscription_info["subscription"]
            break
    else:
        await bot.send(event, "未找到订阅信息")
        return

    messages = []
    for subscription in subscription_data:
        message = f'{subscription["code"]}. [{subscription["project_name"]}] {subscription["project_url"]}'
        messages.append({"type": "node", "data": {"name": "订阅项目", "uin": "", "content": message}})

    if source == "Group":
        await bot.call_api("send_group_forward_msg", group_id=event.group_id, messages=messages, sender_id=sender_id)
    else:
        await bot.call_api("send_private_forward_msg", user_id=event.user_id, messages=messages, sender_id=sender_id)

    await view_subscription.finish()


# 定义定时任务，每隔一段时间执行一次
@scheduler.scheduled_job('interval', minutes=1)
async def check_github_info():
    subscriptions = load_subscriptions()
    bot = nonebot.get_bot()

    for sub in subscriptions:
        if sub['push_enabled']:
            try:
                for sub_item in sub["subscription"]:
                    response = requests.get(f"https://api.github.com/repos/{sub_item['project_name']}")
                    data = response.json()
                    issues_count = data.get('open_issues_count', 0)
                    stars_count = data.get('stargazers_count', 0)
                    last_update = data.get('updated_at', '')
                    message = f"{sub_item['project_name']}更新情况：\nIssues数量：{issues_count}\nStars数量：{stars_count}\n最后更新日期：{last_update}"
                    if sub['source'] == "Group":
                        await bot.call_api("send_group_msg", group_id=sub['ID'], message=message)
                    else:
                        await bot.call_api("send_private_msg", user_id=sub['ID'], message=message)
            except Exception as e:
                logger.error(f"检查 GitHub 项目时出错: {e}")

check_github_test = on_regex(
    r"^(查询(github|GitHub|)(订阅)(.*)(github.com))", priority=1
)
#  手动查看订阅信息
@check_github_test.handle()
async def check_github_test_plugin(bot: Bot, event: Event) -> None:
    # bot = nonebot.get_bot()
    # bot_name = str(bot.config.nickname)
    # nickname = bot_name.replace("{", "").replace("}", "").replace("'", "")
    get_project_message = str(event.get_message())
    get_project_name = r"https://github.com/(.+)"
    project_name = re.search(get_project_name, get_project_message)
    if project_name:
        project_name = project_name.group(1)
    else:
        project_name = "未匹配到项目名称"
        await bot.send(event, f"无法查询到需要订阅的信息，请检查重试")
    try:
        response = requests.get(f"https://api.github.com/repos/{project_name}")
        await bot.send(event, f"https://api.github.com/repos/{project_name}")
        data = response.json()
        issues_count = data.get('open_issues_count', 0)
        stars_count = data.get('stargazers_count', 0)
        last_update = data.get('updated_at', '')
        message = f"{project_name}当前情况：\nIssues数量：{issues_count}\nStars数量：{stars_count}\n最后更新日期：{last_update}"
        bot = nonebot.get_bot()
        if isinstance(event, PrivateMessageEvent):
            source = "Private"
            ID = event.user_id
        else:
            source = "Group"
            ID = event.group_id

        if source == "Group":
            await bot.call_api("send_group_forward_msg", group_id=event.group_id, message=message, sender_id=ID)
        else:
            await bot.call_api("send_private_forward_msg", user_id=event.user_id, message=message, sender_id=ID)
    except Exception as e:
        logger.error(f"检查 GitHub 项目时出错: {e}")
        await bot.send(logger.error)



enable_subscription_push = on_command('开启订阅推送', permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER)


# 开启订阅推送
@enable_subscription_push.handle()
async def enable_subscription_push_plugin(bot: Bot, event: Event):
    subscriptions = load_subscriptions()
    # 判断消息来源
    try:
        if event.group_id:
            source = "Group"
    except:
        source = "Private"
    ID = event.group_id if source == "Group" else event.user_id

    for sub in subscriptions:
        if sub.get('source') == source and sub.get('ID') == ID:
            if sub.get('push_enabled') == True:
                await bot.send(event, "当前已开启订阅推送功能，无需重复开启！")
                return
            sub['push_enabled'] = True
            save_subscriptions(subscriptions)
            await bot.send(event, "已开启订阅推送功能")
            return
    await bot.send(event, "未找到对应的订阅信息")




disable_subscription_push = on_command('关闭订阅推送', permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER)

# 关闭订阅推送
@disable_subscription_push.handle()
async def disable_subscription_push_plugin(bot: Bot, event: Event):
    subscriptions = load_subscriptions()
    # 判断消息来源
    try:
        if event.group_id:
            source = "Group"
    except:
        source = "Private"
    ID = event.group_id if source == "Group" else event.user_id

    for sub in subscriptions:
        if sub.get('source') == source and sub.get('ID') == ID:
            if sub.get('push_enabled') == False:
                await bot.send(event, "当前已关闭订阅推送功能，无需重复关闭！")
                return
            sub['push_enabled'] = False
            save_subscriptions(subscriptions)
            await bot.send(event, "已关闭订阅推送功能")
            return
    await bot.send(event, "未找到对应的订阅信息")
