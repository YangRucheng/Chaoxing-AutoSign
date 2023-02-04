from .config import API_KEY, SECRET_KEY
from pyzxing import BarCodeReader
import tempfile
import httpx
import os

reader = BarCodeReader()


class OCR(object):
    """ 识别二维码中的文本 """
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }

    def __init__(self) -> None:
        self.client = httpx.AsyncClient(
            http2=True, timeout=3.0, headers=self.headers)

    async def __call__(self, path: str) -> str:
        resp = await self.client.get(path)
        img = resp.content
        data = self.QRcode(None, img)
        if data.get('raw'):
            return data['raw']
        else:
            url = "https://aip.baidubce.com/rest/2.0/ocr/v1/qrcode?access_token={0}"
            data = {'url': path}
            try:
                resp = await self.client.post(url.format(await self.__getToken()), data=data)
                text = resp.json()['codes_result'][0]['text'][0]
            except:
                return "error"
            else:
                return text

    async def __getToken(self):
        """ 使用 AK SK 生成鉴权签名 Access Token """
        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {"grant_type": "client_credentials",
                  "client_id": API_KEY, "client_secret": SECRET_KEY}
        resp = await self.client.post(url, params=params)
        return str(resp.json().get("access_token"))

    @staticmethod
    def QRcode(path: str = None, file: bytes = None) -> dict:
        """ 识别二维码 """
        if path:
            result: dict[bytes] = reader.decode(path)[0]
        elif file:
            f, path = tempfile.mkstemp()
            try:
                with os.fdopen(f, 'wb') as tmp:
                    tmp.write(file)
                result: dict[bytes] = reader.decode(path)[0]
            finally:
                os.remove(path)
        for key in result.keys():
            if type(result[key]) == bytes:
                result[key] = result[key].decode()
        return result
