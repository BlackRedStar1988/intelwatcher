import sys
import time
import argparse
import random

def mechanize_cookie(config):
    import mechanize

    print("Logging into Facebook using mechanize")
    def select_form():
        browser.select_form(nr=0)
        browser.form['email'] = config.ingress_user
        browser.form['pass'] = config.ingress_password
        response = browser.submit()
        return response

    browser = mechanize.Browser()
    browser.set_handle_robots(False)
    cookies = mechanize.CookieJar()
    browser.set_cookiejar(cookies)
    browser.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US) AppleWebKit/534.7 (KHTML, like Gecko) Chrome/7.0.517.41 Safari/534.7')]
    browser.set_handle_refresh(False)

    url = 'https://www.facebook.com/v3.2/dialog/oauth?client_id=449856365443419&redirect_uri=https%3A%2F%2Fintel.ingress.com%2F'
    browser.open(url)

    # sometimes you have to fill in the form multiple times for whatever reason
    tries = 0
    while not "https://intel.ingress.com/" in browser.geturl() and tries < 5:
        response = select_form()
        tries += 1
        time.sleep(2)

    # this is magic
    req = mechanize.Request(browser.geturl())
    cookie_list = browser._ua_handlers['_cookies'].cookiejar.make_cookies(response, req)

    cookies = {c.name: c.value for c in cookie_list}
    final_cookie = ''.join("{}={}; ".format(k, v) for k, v in cookies.items())

    print("Your cookie:")
    print(final_cookie)

    with open('cookie.txt', encoding='utf-8', mode='w') as cookie:
        cookie.write(final_cookie)

    return final_cookie

def selenium_cookie(config):
    from pathlib import Path
    from selenium import webdriver
    from selenium.common.exceptions import NoSuchElementException
    from selenium.webdriver.common.by import By

    def _debug_save_screenshot(debug, driver, filename):
        if debug:
            driver.save_screenshot(filename)
        driver.quit()
        sys.exit(1)

    def _write_cookie(driver):
        print('Getting cookies...')
        cookies = {c['name']: c['value'] for c in driver.get_cookies()}

        with open('cookie.txt', encoding='utf-8', mode='w') as cookie:
            print('Write cookie data into "cookie.txt"...')
            cookie.write(''.join("{}={}; ".format(k, v) for k, v in cookies.items()))

    if config.debug:
        debug_dir = Path(__file__).resolve().parent / 'debug'
        debug_dir.mkdir(exist_ok=True)

    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3072.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0',
        'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.87 Safari/537.36 OPR/37.0.2178.32',
        'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/534.57.2 (KHTML, like Gecko) Version/5.1.7 Safari/534.57.2',
        'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.101 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.101 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2486.0 Safari/537.36 Edge/13.10586',
        'Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko',
        'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 BIDUBrowser/8.3 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Maxthon/4.9.2.1000 Chrome/39.0.2146.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 61; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.80 Safari/537.36 Core/1.47.277.400 QQBrowser/9.4.7658.400',
        'Mozilla/5.0 (Linux; Android 5.0; SM-N9100 Build/LRX21V) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/37.0.0.0 Mobile Safari/537.36 MicroMessenger/6.0.2.56_r958800.520 NetType/WIFI',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 7_1_2 like Mac OS X) AppleWebKit/537.51.2 (KHTML, like Gecko) Mobile/11D257 QQ/5.2.1.302 NetType/WIFI Mem/28'
    ]

    user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.50 Safari/537.36'

    if config.webdriver == 'firefox':
        options = webdriver.FirefoxOptions()
    else:
        options = webdriver.ChromeOptions()
        options.add_argument(f'user-agent={user_agent}')

    if config.headless_mode:
        options.add_argument('--headless')

    if config.webdriver == 'firefox':
        from webdriver_manager.firefox import GeckoDriverManager

        options.add_argument('--new-instance')
        options.add_argument('--safe-mode')

        driver = webdriver.Firefox(executable_path=GeckoDriverManager().install(), options=options)
    else:
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')

        if config.webdriver == 'chromium':
            from webdriver_manager.chrome import ChromeDriverManager
            from webdriver_manager.utils import ChromeType

            driver = webdriver.Chrome(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install(), options=options)
        else:
            from webdriver_manager.chrome import ChromeDriverManager

            driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)

    if config.ingress_login_type == 'google':
        print('Login to Google via Stackoverflow')
        driver.get('https://stackoverflow.com/users/login?ssrc=head')

        try:
            driver.find_element(By.CSS_SELECTOR, f'.s-btn__{config.ingress_login_type}').click()
            driver.implicitly_wait(10)
        except NoSuchElementException:
            _debug_save_screenshot(config.debug, driver, str(debug_dir) + '/google_login_init.png')

        print('Enter username...')
        try:
            driver.find_element(By.ID, 'identifierId').send_keys(config.ingress_user)
            driver.find_element(By.ID, 'identifierNext').click()
            driver.implicitly_wait(10)
        except NoSuchElementException:
            _debug_save_screenshot(config.debug, driver, str(debug_dir) + '/google_login_username.png')

        print('Enter password...')
        try:
            pw_element = driver.find_element(By.ID, 'password').find_element(By.NAME, 'password')

            if config.webdriver == 'firefox':
                # to make element visible:
                driver.execute_script(
                    'arguments[0].style = ""; arguments[0].style.display = "block"; arguments[0].style.visibility = "visible";',
                    pw_element
                )
                time.sleep(1)

            pw_element.send_keys(config.ingress_password)
            driver.find_element(By.ID, 'passwordNext').click()
            driver.implicitly_wait(10)
        except NoSuchElementException:
            _debug_save_screenshot(config.debug, driver, str(debug_dir) + '/google_login_password.png')

        print('Waiting for login...')
        time.sleep(5)

        print('Login to Intel Ingress')
        try:
            driver.get('https://accounts.google.com/o/oauth2/v2/auth?client_id=369030586920-h43qso8aj64ft2h5ruqsqlaia9g9huvn.apps.googleusercontent.com&redirect_uri=https://intel.ingress.com/&prompt=consent%20select_account&state=GOOGLE&scope=email%20profile&response_type=code')
            driver.find_element(By.ID, 'profileIdentifier').click()
            driver.implicitly_wait(10)
        except NoSuchElementException:
            _debug_save_screenshot(config.debug, driver, str(debug_dir) + '/intel_login_init.png')

        print('Waiting for login...')
        time.sleep(5)
        _write_cookie(driver)
    elif config.ingress_login_type == 'facebook':
        driver.get('http://intel.ingress.com')
        driver.find_element(By.XPATH, '//div[@id="dashboard_container"]//a[@class="button_link" and contains(text(), "Facebook")]').click()
        driver.implicitly_wait(10)

        print('Enter username...')
        try:
            driver.find_element(By.ID, 'email').send_keys(config.ingress_user)
        except NoSuchElementException:
            _debug_save_screenshot(config.debug, driver, str(debug_dir) + '/fb_login_username.png')

        print('Enter password...')
        try:
            driver.find_element(By.ID, 'pass').send_keys(config.ingress_password)
        except NoSuchElementException:
            _debug_save_screenshot(config.debug, driver, str(debug_dir) + '/fb_login_password.png')

        print('Waiting for login...')
        try:
            driver.find_element(By.ID, 'loginbutton').click()
            driver.implicitly_wait(10)
        except NoSuchElementException:
            _debug_save_screenshot(config.debug, driver, str(debug_dir) + '/fb_login_login.png')

        time.sleep(5)

        print('Confirm oauth login when needed...')
        try:
            driver.find_element(By.ID, 'platformDialogForm').submit()
            driver.implicitly_wait(10)
            time.sleep(5)
        except NoSuchElementException:
            pass

        _write_cookie(driver)

    driver.quit()

if __name__ == '__main__':
    print('Initializing...')

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', default='config.ini', help='Config file to use')
    args = parser.parse_args()
    config_path = args.config

    config = SeleniumConfig(config_path)

    get_ingress_cookie(config)
