import time
import argparse

from selenium import webdriver
from selenium.webdriver.common.by import By
from util.config import SeleniumConfig


def get_ingress_cookie(config):
    user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.50 Safari/537.36'

    if config.webdriver == 'firefox':
        options = webdriver.FirefoxOptions()
    else:
        options = webdriver.ChromeOptions()
        options.add_argument(f'user-agent={user_agent}')

    options.add_argument("--headless")

    if config.webdriver == 'chromium':
        from webdriver_manager.chrome import ChromeDriverManager
        from webdriver_manager.utils import ChromeType

        driver = webdriver.Chrome(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install(), options=options)
    elif config.webdriver == 'firefox':
        from webdriver_manager.firefox import GeckoDriverManager

        driver = webdriver.Firefox(executable_path=GeckoDriverManager().install(), options=options)
    else:
        from webdriver_manager.chrome import ChromeDriverManager

        driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)

    if config.ingress_login_type == 'google':
        print('Login to Google via Stackoverflow')
        driver.get('https://stackoverflow.com/users/login?ssrc=head')

        driver.find_element(By.CSS_SELECTOR, f'.s-btn__{config.ingress_login_type}').click()
        driver.implicitly_wait(10)

        print('Enter username...')
        driver.find_element(By.ID, 'identifierId').send_keys(config.ingress_user)
        driver.find_element(By.ID, 'identifierNext').click()
        driver.implicitly_wait(10)

        print('Enter password...')
        driver.find_element(By.ID, 'password').find_element(By.TAG_NAME, 'input').send_keys(config.ingress_password)
        driver.find_element(By.ID, 'passwordNext').click()
        driver.implicitly_wait(10)

        print('Waiting for login...')
        time.sleep(5)

        print('Login to Intel Ingress')
        driver.get('https://accounts.google.com/o/oauth2/v2/auth?client_id=369030586920-h43qso8aj64ft2h5ruqsqlaia9g9huvn.apps.googleusercontent.com&redirect_uri=https://intel.ingress.com/&prompt=consent%20select_account&state=GOOGLE&scope=email%20profile&response_type=code')
        driver.find_element(By.ID, 'profileIdentifier').click()
        driver.implicitly_wait(10)

        print('Waiting for login...')
        time.sleep(5)

        print('Getting cookies...')
        cookies = {c['name']: c['value'] for c in driver.get_cookies()}

        with open('cookie.txt', encoding='utf-8', mode='w') as cookie:
            print('Write cookie data into "cookie.txt"...')
            cookie.write(''.join("{}={}; ".format(k, v) for k, v in cookies.items()))

    driver.quit()


if __name__ == '__main__':
    print('Initializing...')

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', default='config.ini', help='Config file to use')
    args = parser.parse_args()
    config_path = args.config

    config = SeleniumConfig(config_path)

    get_ingress_cookie(config)
