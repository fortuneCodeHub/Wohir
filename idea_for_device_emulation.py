# cd: tests/test_mobile_cdp.py
from seleniumbase import BaseCase

class TestMobileCDP(BaseCase):
    def test_emulate_iphone_x(self):
        # Set viewport + DPR + mobile flag
        metrics = {
            "width": 375,
            "height": 812,
            "deviceScaleFactor": 3,
            "mobile": True
        }
        # Set user agent to a mobile UA
        ua = ("Mozilla/5.0 (iPhone; CPU iPhone OS 13_0 like Mac OS X) "
              "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0 Mobile/15E148 Safari/604.1")

        # Execute Chrome DevTools Protocol commands (Chromium-only)
        self.driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", metrics)
        self.driver.execute_cdp_cmd("Emulation.setUserAgentOverride", {"userAgent": ua})

        # Now open site — the session behaves like the emulated device
        self.open("https://example.com")
        # Example assertion that should be true on mobile layouts
        # (Adjust selector to your target site)
        self.assert_element("meta[name='viewport']")





test = TestMobileCDP()
test.test_emulate_iphone_x()