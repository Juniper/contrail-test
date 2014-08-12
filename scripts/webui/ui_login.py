from selenium import webdriver
from pyvirtualdisplay import Display
from webui.webui_common import *
from selenium.common.exceptions import WebDriverException
import os

class UILogin:
    browser = None
    browser_openstack = None
    os_url = None
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
        self.ui_flag = self.inputs.webui_verification_flag
        self._start_virtual_display()
        if self.ui_flag == 'chrome':
            chromedriver = "/usr/bin/chromedriver"
            os.environ["webdriver.chrome.driver"] = chromedriver
            options = webdriver.ChromeOptions()
            options.add_argument("test-type")
        self.webui_common = WebuiCommon(self)
        if not UILogin.os_url:
            url_string = "http://" + self.inputs.openstack_ip
            if self.os_name == 'ubuntu':
                UILogin.os_url = url_string + "/horizon"
            else:
                UILogin.os_url = url_string + "/dashboard"
        if not UILogin.browser:
            if self.ui_flag == 'firefox':
                UILogin.browser = webdriver.Firefox()
                UILogin.browser_openstack = webdriver.Firefox()
            elif self.ui_flag == 'chrome':
                UILogin.browser = webdriver.Chrome(chromedriver, chrome_options=options)
                UILogin.browser_openstack = webdriver.Chrome(chromedriver, chrome_options=options)
            else:
                self.inputs.logger.error("Invalid browser type")
            self.webui(self.username, self.password)
            self.openstack(self.username, self.password)
    #end __init__

    def __del__(self):
        self._close()
        pass
    #end __del__

    def _close(self):
        self.browser.quit()
        self.browser_openstack.quit()
        self.inputs.logger.info("%s browser closed...." %(self.ui_flag.title()))
        self.display.stop()
        self.inputs.logger.info("Virtual display stopped...")
    #end _close

    def openstack(self,  username, password):
        self._launch(self.browser_openstack)
        self._set_display(self.browser_openstack)
        self.login(self.browser_openstack, self.os_url, username, password)
    #end login_openstack

    def _launch(self, browser):
        if browser:
            self.inputs.logger.info("%s browser launched...." %
                                    (self.ui_flag.title()))
        else:
            self.inputs.logger.info(
                "Problem occured while browser launch....")
    #end launch

    def _set_display(self, browser):
        browser.set_window_position(0, 0)
        browser.set_window_size(1280, 1024)
    #end set_display

    def _start_virtual_display(self):
        self.display = None
        self.display = Display(visible=0, size=(800, 600))
        self.display.start()
        if self.display:
            self.inputs.logger.info(
                "Virtual display started..running webui tests....")
    #end start_virtual_display

    def webui(self, username, password):
        self._launch(self.browser)
        self._set_display(self.browser)
        url = 'http://' + self.inputs.webui_ip + ':8080'
        self.login(self.browser, url, username, password)
    #end login_webui

    def login(self, browser, url,  user, password):
        login = None
        obj = self.webui_common        
        self.inputs.logger.info("Opening " + url)
        browser.get(url)
        try:
            if url.find('8080') != -1:
                obj.find_element(browser, 'btn-monitor', 'id') 
            else:
                obj.find_element(browser, 'container', 'id')
            self.inputs.logger.info(url + " User already logged in")
            login = True
        except WebDriverException:    
            self.inputs.logger.info(url + " User is not logged in")
            pass
        if not login :
            try: 
                obj.send_keys(user, browser, 'username', 'name')
                obj.send_keys(password, browser,'password', 'name')
                obj.click_element(browser, 'btn')
                if url.find('8080') != -1:
                    obj.find_element(browser, 'btn-monitor', 'id')
                else:
                    obj.find_element(browser, 'container', 'id')
                self.inputs.logger.info(url + " login successful....")
            except WebDriverException:
                self.inputs.logger.error(url + " Not able to login ..capturing screenshot.")
                self.browser.get_screenshot_as_file('url_login_failed_' + obj.date_time_string() + '.png')
                sys.exit(-1)
    #end login
