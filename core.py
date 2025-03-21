import json
from selenium import webdriver
from selenium.webdriver.edge.options import Options  # 使用 Edge
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.edge.service import Service  # 使用 Edge

def fetch_data_with_selenium(match_id):
    api_url = f"https://api.haojiao.cc/wiki/api/v1/foresight/valorant_player?match_id={match_id}"

    # 配置 Edge 选项
    edge_options = Options()
    edge_options.add_argument("--headless")
    # edge_options.add_argument('--ignore-certificate-errors')  # 如果需要忽略 SSL 错误

    # 启动 Edge 浏览器
    service = Service(executable_path="driver\\msedgedriver.exe")  # 替换为您的 Edge WebDriver 路径
    driver = webdriver.Edge(service=service, options=edge_options)

    print("Edge 启动成功")

    try:
        # 打开网页
        driver.get(f"https://web.haojiao.cc/wiki/match/t2Ud5pOQlscKLbRC/{match_id}")

        # 监听网络请求 (使用 JavaScript)
        driver.execute_script("""
            window.performance.setResourceTimingBufferSize(1000); // 增加缓冲区大小 (可选)
            window.requests = [];
            window.addEventListener('load', function() {
                window.performance.getEntriesByType('resource').forEach(function(entry) {
                    if (entry.initiatorType === 'xmlhttprequest' || entry.initiatorType === 'fetch') {
                        window.requests.push({url: entry.name, response: null});
                    }
                });
                // 获取响应内容 (需要异步操作)
                window.requests.forEach(function(request, index) {
                    fetch(request.url)
                        .then(response => response.json())
                        .then(data => {
                            window.requests[index].response = data;
                         })
                        .catch(error=>console.log(error));
                });
            });
        """)

        # 等待页面加载完成 (这里我们等待 API 请求完成 - 更可靠的方法)
        #   我们可以设置一个合理的超时时间，例如 30 秒
        WebDriverWait(driver, 30).until(
            lambda d: any(req['url'] == api_url and req['response'] is not None for req in d.execute_script("return window.requests"))
        )

        # 获取包含 JSON 响应的网络请求
        requests = driver.execute_script("return window.requests")
        json_data = None
        for req in requests:
            if req['url'] == api_url and req['response'] is not None:
                json_data = req['response']
                break

        return json_data

    except TimeoutException:
        print("等待超时，未能加载所需 API 响应")
        return None
    except Exception as e:
        print(f"Selenium 抓取出错: {e}")
        return None
    finally:
        driver.quit()

# 使用
match_id = "IJ2Nr2rJM9NjQJMO"
data = fetch_data_with_selenium(match_id)
if data:
    print(json.dumps(data, indent=4, ensure_ascii=False))