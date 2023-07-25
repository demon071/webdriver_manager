from packaging import version

from webdriver_manager.core.driver import Driver
from webdriver_manager.core.logger import log
from webdriver_manager.core.os_manager import OperationSystemManager, ChromeType


class ChromeDriver(Driver):

    def __init__(
            self,
            name,
            driver_version,
            url,
            latest_release_url,
            http_client,
            os_system_manager,
            chrome_type=ChromeType.GOOGLE
    ):
        super(ChromeDriver, self).__init__(
            name,
            driver_version,
            url,
            latest_release_url,
            http_client,
            os_system_manager
        )
        self._browser_type = chrome_type
        self._os_type = self.get_os_type()

    def get_os_type(self):
        os_type = super().get_os_type()
        if "win" in os_type:
            return "win32"

        if not OperationSystemManager.is_mac_os(os_type):
            return os_type

        if OperationSystemManager.is_arch(os_type):
            return "mac_arm64"

        return os_type

    def get_driver_download_url(self):
        driver_version_to_download = self.get_driver_version_to_download()
        os_type = self._os_type
        # For Mac ARM CPUs after version 106.0.5249.61 the format of OS type changed
        # to more unified "mac_arm64". For newer versions, it'll be "mac_arm64"
        # by default, for lower versions we replace "mac_arm64" to old format - "mac64_m1".
        if version.parse(driver_version_to_download) < version.parse("106.0.5249.61"):
            os_type = os_type.replace("mac_arm64", "mac64_m1")

        if version.parse(driver_version_to_download) >= version.parse("115"):
            if os_type == "mac64":
                os_type = "mac-x64"
            if os_type in ["mac_64", "mac64_m1", "mac_arm64"]:
                os_type = "mac-arm64"

            modern_version_url = self.get_url_for_version_and_platform(driver_version_to_download, os_type)
            log(f"Modern chrome version {modern_version_url}")
            return modern_version_url

        return f"{self._url}/{driver_version_to_download}/{self.get_name()}_{os_type}.zip"

    def get_browser_type(self):
        return self._browser_type

    def get_latest_release_version(self):
        def convert_version(version):
            # Tách version thành các phần bằng dấu chấm (.)
            version_parts = version.split(".")
            
            # Nếu version có ít hơn 4 phần, trả về version ban đầu
            if len(version_parts) < 4:
                return version

            # Chuyển đổi lại thành version chỉ chứa 3 phần đầu tiên
            new_version = ".".join(version_parts[:3])
            return new_version
        determined_browser_version = self.get_browser_version_from_os()
        log(f"Get LATEST {self._name} version for {self._browser_type}")
        if version.parse(determined_browser_version) >= version.parse("115"):
            return determined_browser_version

        latest_release_url = (
            self._latest_release_url
            if (self._driver_version == "latest" or determined_browser_version is None)
            else f"{self._latest_release_url}_{convert_version(determined_browser_version)}"
        )
        resp = self._http_client.get(url=latest_release_url)
        return resp.text.rstrip()

    def get_url_for_version_and_platform(self, browser_version, platform):
        url = "https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json"
        response = self._http_client.get(url)
        data = response.json()
        versions = [version for version in data['versions'] if browser_version.split('.')[0] in version['version'] and 'chromedriver' in version['downloads']]
        max_version = versions[0]
        for v in versions:
            if v["version"] == browser_version:
                downloads = v["downloads"]["chromedriver"]
                for d in downloads:
                    if d["platform"] == platform:
                        return d["url"]
            elif version.parse(v['version']) < version.parse(browser_version) and version.parse(v['version']) > version.parse(max_version['version']):
                max_version = v
        downloads = max_version["downloads"]["chromedriver"]
        for d in downloads:
            if d["platform"] == platform:
                return d["url"]

        raise Exception(f"No such driver version {browser_version} for {platform}")
