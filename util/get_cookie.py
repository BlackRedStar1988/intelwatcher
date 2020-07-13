import sys
import os
import time
import logging
import glob


def _write_cookie(cookies):
    final_cookie = ''.join("{}={}; ".format(k, v) for k, v in cookies.items())
    with open('cookie.txt', encoding='utf-8', mode='w') as cookie:
        print('Write cookie to cookie.txt...')
        cookie.write(final_cookie)

    print("Your cookie:")
    print(final_cookie)

    return final_cookie


def mechanize_cookie(config):
    """Returns a new Intel Ingress cookie via mechanize."""
    import mechanize

    print("Logging into Facebook using mechanize")
    browser = mechanize.Browser()

    if config.debug:
        logger = logging.getLogger('mechanize')
        logger.addHandler(logging.StreamHandler(sys.stdout))
        logger.setLevel(logging.DEBUG)

        browser.set_debug_http(True)
        browser.set_debug_responses(True)
        browser.set_debug_redirects(True)

    browser.set_handle_robots(False)
    cookies = mechanize.CookieJar()
    browser.set_cookiejar(cookies)
    browser.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US) AppleWebKit/534.7 (KHTML, like Gecko) Chrome/7.0.517.41 Safari/534.7')]
    browser.set_handle_refresh(False)
    print("Everything set - Let's go")

    url = 'https://www.facebook.com/v3.2/dialog/oauth?client_id=449856365443419&redirect_uri=https%3A%2F%2Fintel.ingress.com%2F'
    browser.open(url)
    print("Opened Facebook Login Page")

    # sometimes you have to fill in the form multiple times for whatever reason
    tries = 0
    while "https://intel.ingress.com/" not in browser.geturl() and tries < 5:
        tries += 1
        print(f"Trying to log into Intel: Try {tries}/5")
        browser.select_form(nr=0)
        browser.form['email'] = config.ingress_user
        browser.form['pass'] = config.ingress_password
        response = browser.submit()
        time.sleep(2)

    if "https://intel.ingress.com/" in response.geturl() and response.getcode() == 200:
        print("Got through. Now getting that cookie")

        # this is magic
        req = mechanize.Request(browser.geturl())
        cookie_list = browser._ua_handlers['_cookies'].cookiejar.make_cookies(response, req)

        final_cookie = _write_cookie({c.name: c.value for c in cookie_list})
        return final_cookie
    else:
        print("Error: failed to login into Intel")
        return ""


def selenium_cookie(config):
    """Returns a new Intel Ingress cookie via selenium webdriver."""
    from pathlib import Path
    from selenium import webdriver
    from selenium.common.exceptions import NoSuchElementException
    from selenium.webdriver.common.by import By

    def _save_screenshot_on_failure(filename):
        driver.save_screenshot('{}/{}'.format(str(debug_dir), filename))
        driver.quit()
        sys.exit(1)

    debug_dir = Path(__file__).resolve().parent.parent / 'debug'
    debug_dir.mkdir(exist_ok=True)

    # cleanup screenshots
    files = glob.glob('{}/*.png'.format(str(debug_dir)))
    for f in files:
        os.remove(f)

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
            _save_screenshot_on_failure('google_login_init.png')

        print('Enter username...')
        try:
            driver.find_element(By.ID, 'identifierId').send_keys(config.ingress_user)
            driver.find_element(By.ID, 'identifierNext').click()
            driver.implicitly_wait(10)
        except NoSuchElementException:
            _save_screenshot_on_failure('google_login_username.png')

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
            _save_screenshot_on_failure('google_login_password.png')

        print('Waiting for login...')
        time.sleep(5)

        if 'https://accounts.google.com/' in driver.current_url:
            print('Failed to login into Google')
            _save_screenshot_on_failure('google_login_security.png')

        print('Login to Intel Ingress')
        try:
            driver.get('https://accounts.google.com/o/oauth2/v2/auth?client_id=369030586920-h43qso8aj64ft2h5ruqsqlaia9g9huvn.apps.googleusercontent.com&redirect_uri=https://intel.ingress.com/&prompt=consent%20select_account&state=GOOGLE&scope=email%20profile&response_type=code')
            driver.find_element(By.ID, 'profileIdentifier').click()
            driver.implicitly_wait(10)
        except NoSuchElementException:
            _save_screenshot_on_failure('intel_login_init.png')

        print('Waiting for login...')
        time.sleep(5)
        final_cookie = _write_cookie({c['name']: c['value'] for c in driver.get_cookies()})
    elif config.ingress_login_type == 'facebook':
        driver.get('http://intel.ingress.com')
        driver.find_element(By.XPATH, '//div[@id="dashboard_container"]//a[@class="button_link" and contains(text(), "Facebook")]').click()
        driver.implicitly_wait(10)

        print('Enter username...')
        try:
            driver.find_element(By.ID, 'email').send_keys(config.ingress_user)
        except NoSuchElementException:
            _save_screenshot_on_failure('fb_login_username.png')

        print('Enter password...')
        try:
            driver.find_element(By.ID, 'pass').send_keys(config.ingress_password)
        except NoSuchElementException:
            _save_screenshot_on_failure('fb_login_password.png')

        print('Waiting for login...')
        try:
            driver.find_element(By.ID, 'loginbutton').click()
            driver.implicitly_wait(10)
        except NoSuchElementException:
            _save_screenshot_on_failure('fb_login_login.png')

        time.sleep(5)

        print('Confirm oauth login when needed...')
        try:
            driver.find_element(By.ID, 'platformDialogForm').submit()
            driver.implicitly_wait(10)
            time.sleep(5)
        except NoSuchElementException:
            pass

        final_cookie = _write_cookie({c['name']: c['value'] for c in driver.get_cookies()})

    driver.quit()
    return final_cookie
