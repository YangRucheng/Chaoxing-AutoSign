from bs4 import BeautifulSoup
from urllib import parse
from .二维码 import OCR
import httpx


class ChaoXing(object):
    """ 学习通 """
    username: str
    password: str

    timeout = 3
    max_retry = 3
    cookies = None
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
    }

    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password
        self.client = httpx.AsyncClient(
            http2=True, timeout=self.timeout, headers=self.headers)

    async def login(self):
        """ 登录 """
        url = f"https://passport2-api.chaoxing.com/v11/loginregister?code={self.password}&cx_xxt_passport=json&uname={self.username}&loginType=1&roleSelect=true"
        try:
            resp = await self.client.get(url)
            assert resp.status_code == 200
            assert resp.json()['status'], "登录失败"
        except (Exception, BaseException)as e:
            print(e)
            return False
        else:
            self.cookies = resp.cookies
            self.uid = dict(self.cookies).get(
                'UID', dict(self.cookies).get('_uid', None))
            return True

    async def getCourse(self) -> list[dict]:
        """ 获取课程列表 """
        url = "https://mooc1-api.chaoxing.com/mycourse/backclazzdata?view=json&rss=1"
        try:
            resp = await self.client.get(url, cookies=self.cookies)
            res = resp.json()
            assert res['result'] == 1, "获取课程失败"
        except (Exception, BaseException)as e:
            print(e)
            return []
        else:
            dataList: list[dict] = [
                x for x in res['channelList']
                if (x.get('cataName') == '课程' and x['content'].get('course') and x['cfid'] == -1)]
            self.courses = [{
                '课程': x['content']['course']['data'][0]['name'],
                '班级':x['content']['name'],
                '教师':x['content']['course']['data'][0]['teacherfactor'],
                'courseId':x['content']['course']['data'][0]['id'],
                'classId':x['key']
            } for x in dataList]
            return self.courses

    async def getActivity(self, courseId: int, classId: int) -> list[dict]:
        """ 获取课程的活动列表 """
        url = f"https://mobilelearn.chaoxing.com/v2/apis/active/student/activelist?fid=0&courseId={courseId}&classId={classId}&showNotStartedActive=0"
        try:
            resp = await self.client.get(url, cookies=self.cookies)
            res = resp.json()
            assert res['result'] == 1, "获取活动失败"
        except (Exception, BaseException)as e:
            print(e)
            return []
        else:
            dataList: list[dict] = res['data']['activeList']
            self.activities = [{
                'type': int(x['otherId']),
                'name': x['nameOne'],
                'time': x['nameFour'] if x['nameFour'] else "无",
                'activeId': x['id'],
                'courseId': courseId,
                'classId': classId
            } for x in dataList]
            return self.activities

    async def before(self, courseId: int, classId: int, activeId: int) -> str:
        """ 预签到, 返回HTML """
        url = f"https://mobilelearn.chaoxing.com/newsign/preSign?courseId={courseId}&classId={classId}&activePrimaryId={activeId}&general=1&sys=1&ls=1&appType=15&tid=&uid={self.uid}&ut=s"
        try:
            resp = await self.client.get(url, cookies=self.cookies)
            assert resp.status_code == 200, "预签到失败"
        except (Exception, BaseException)as e:
            print(e)
            return f"error {e}"
        else:
            return resp.text

    async def default(self, activeId: int, objectId: int = 0) -> str:
        """ 普通签到 """
        url = f"https://mobilelearn.chaoxing.com/pptSign/stuSignajax?activeId={activeId}&objectId={objectId}"
        try:
            resp = await self.client.get(url, cookies=self.cookies)
            assert resp.status_code == 200, "签到失败"
        except (Exception, BaseException)as e:
            print(e)
            return str(e)
        else:
            return resp.text

    async def position(self, activeId: int, html: str):
        """ 位置签到 """
        soup = BeautifulSoup(html, 'html.parser')
        locationText = soup.find('input', id='locationText')
        locationLatitude = soup.find('input', id='locationLatitude')
        locationLongitude = soup.find('input', id='locationLongitude')
        url = f"https://mobilelearn.chaoxing.com/pptSign/stuSignajax?address={locationText}&activeId={activeId}&latitude={locationLatitude}&longitude={locationLongitude}&fid=0&appType=15&ifTiJiao=1"
        try:
            resp = await self.client.get(url, cookies=self.cookies)
            assert resp.status_code == 200, "签到失败"
        except (Exception, BaseException)as e:
            print(e)
            return str(e)
        else:
            return resp.text

    async def QRcode(self, activeId: int, enc: str) -> str:
        """ 二维码签到 """
        url = f"https://mobilelearn.chaoxing.com/pptSign/stuSignajax?activeId={activeId}&enc={enc}&fid=0"
        try:
            resp = await self.client.get(url, cookies=self.cookies)
            assert resp.status_code == 200, "签到失败"
        except (Exception, BaseException)as e:
            print(e, enc)
            return str(e)
        else:
            return resp.text

    @staticmethod
    async def getEnc(path: str) -> str:
        """ 获取二维码中的enc参数 """
        try:
            ocr = OCR()
            res = await ocr(path)
            params = parse.parse_qs(parse.urlparse(res).query)
            enc = params.get('enc')[0]
        except (Exception, BaseException) as e:
            raise Exception(f"获取enc失败 {e}")
        else:
            return enc

    async def uploadFile(self, file: bytes, filename: str = "default.jpg") -> str:
        """ 上传文件到超星云盘, 返回objectId """
        try:
            url = "https://pan-yz.chaoxing.com/api/token/uservalid"
            resp = await self.client.get(url, cookies=self.cookies)
            token = resp.json().get('_token')
            url = f"https://pan-yz.chaoxing.com/upload?_token={token}"
            files = {'file': (filename, file)}
            data = {'puid': self.uid}
            resp = await self.client.post(url, files=files, data=data)
            res: dict = resp.json()
        except (Exception, BaseException)as e:
            print(e)
            return f"error {e}"
        else:
            return res.get('objectId')

    @staticmethod
    async def downloadFile(url: str) -> bytes:
        """ 通过URL下载文件 """
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
        return resp.content
