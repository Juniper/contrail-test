from selenium import webdriver
from pyvirtualdisplay import Display
from webui_common import *
from selenium.common.exceptions import WebDriverException
import os
import time
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary


class UILogin:
    browser = None
    browser_openstack = None
    os_url = None
    webui_url = None

    def __init__(self, connections, inputs, project, user, pwd):
        self.project_name = project
        self.username = user
        self.password = pwd
        self.inputs = inputs
        self.connections = connections
        self.logger = self.inputs.logger
        self.delay = 10
        self.frequency = 1
        self.logger = inputs.logger
        self.os_type = self.inputs.os_type
        self.os_name = self.os_type[self.inputs.webui_ip]
        self.ui_flag = self.inputs.ui_browser
        if self.ui_flag == 'chrome':
            chromedriver = "/usr/bin/chromedriver"
            os.environ["webdriver.chrome.driver"] = chromedriver
            options = webdriver.ChromeOptions()
            options.add_argument("test-type")
        self.webui_common = WebuiCommon(self)
        not_supported = ['ie', 'opera', 'safari', 'android']
        if not UILogin.os_url:
            url_string = "http://" + self.inputs.openstack_ip
            if self.os_name == 'ubuntu':
                UILogin.os_url = url_string + "/horizon"
            else:
                UILogin.os_url = url_string + "/dashboard"
            UILogin.webui_url = 'http://' + self.inputs.webui_ip + ':8080'
        if not UILogin.browser:
            self._start_virtual_display()
            if self.ui_flag == 'firefox':
                firefoxdriver = "/usr/bin/firefox"
                os.environ["webdriver.firefox.driver"] = firefoxdriver
                binary = FirefoxBinary(firefoxdriver)
                UILogin.browser = webdriver.Firefox(firefox_binary=binary)
                UILogin.browser_openstack = webdriver.Firefox(
                    firefox_binary=binary)
            elif self.ui_flag == 'chrome':
                UILogin.browser = webdriver.Chrome(
                    chromedriver,
                    chrome_options=options)
                UILogin.browser_openstack = webdriver.Chrome(
                    chromedriver,
                    chrome_options=options)
            elif self.ui_flag in not_supported:
                self.inputs.logger.error(
                    "%s browser type not supported" %
                    (self.ui_flag))
            else:
                self.inputs.logger.error("Invalid browser type")
            self.webui(self.username, self.password)
            self.openstack(self.username, self.password)
    # end __init__

    def __del__(self):
        self._close()
        pass
    # end __del__

    def _close(self):
        self.browser.quit()
        self.browser_openstack.quit()
        self.inputs.logger.info(
            "%s browser closed...." %
            (self.ui_flag.title()))
        self.display.stop()
        self.inputs.logger.info("Virtual display stopped...")
    # end _close

    def openstack(self, username, password):
        self._launch(self.browser_openstack)
        self._set_display(self.browser_openstack)
        self.get_login_page(self.browser_openstack, self.os_url)
        self.login(self.browser_openstack, self.os_url, username, password)
    # end login_openstack

    def _launch(self, browser):
        if browser:
            self.inputs.logger.info("%s browser launched...." %
                                    (self.ui_flag.title()))
        else:
            self.inputs.logger.info(
                "Problem occured while browser launch....")
    # end launch

    def _set_display(self, browser):
        browser.set_window_position(0, 0)
        browser.set_window_size(1280, 1024)
    # end set_display

    def _start_virtual_display(self):
        self.display = None
        self.display = Display(visible=0, size=(800, 600))
        self.display.start()
        if self.display:
            self.inputs.logger.info(
                "Virtual display started..running webui tests....")
    # end start_virtual_display

    def webui(self, username, password):
        self._launch(self.browser)
        self._set_display(self.browser)
        url = 'http://' + self.inputs.webui_ip + ':8080'
        self.get_login_page(self.browser, url)
        self.login(self.browser, url, username, password)
    # end login_webui

    def get_login_page(self, br, url, wait=5):
        br.get(url)
        time.sleep(wait)
    # end get_login_screen

    def login(self, br, url, user, password):
        login = None
        obj = self.webui_common
        self.get_login_page(br, url, 2)
        try:
            if url.find('8080') != -1:
                obj.find_element('btn-monitor', browser=br, delay=4)
            else:
                br.find_element_by_id('container')
            login = True
        except WebDriverException:
            self.inputs.logger.info(url + " User is not logged in")
            pass
        if not login:
            try:
                obj.send_keys(user, 'username', 'name', browser=br)
                obj.send_keys(password, 'password', 'name', browser=br)
                obj.click_element('btn', 'class', browser=br)
                time.sleep(60)
                try:
                    if url.find('8080') != -1:
                        obj.find_element('btn-monitor', browser=br)
                    else:
                        obj.find_element('container', browser=br)
                except:
                    self.get_login_page(br, url, 2)
                    obj.find_element('btn-monitor', browser=br)
                self.inputs.logger.info(url + " login successful....")
                login = True
            except WebDriverException:
                self.inputs.logger.error(
                    url +
                    " Not able to login ..capturing screenshot.")
                br.get_screenshot_as_file(
                    'url_login_failed_' +
                    obj.date_time_string() +
                    '.png')
        assert login, "Login failed.."
    # end login
