import io
from PIL import Image
from . import Base


class Dummy(Base):
    def boot_driver(self):
        class dummydriver:
            name = "dummy"
            desired_capabilities = {}
            current_url = "http://example.com"
            page_source = "source string"
            title = "title string"
            window_handles = []
            session_id = "dummy"
            current_window_handle = None
            capabilities = None
            log_types = []
            w3c = False

            def __init__(self, dummyparam=None):
                """
                initialize dummy driver with dummy parameters
                """
                super().__init__()

            def find_element(self, k, v):
                return None

            def find_elements(self, k, v):
                return []

            def get_cookies(self):
                return {}

            def get_window_size(self):
                return 0, 0

            def get_window_position(self):
                return 0, 0

            def close(self):
                pass

            def quit(self):
                pass

            def get_screenshot_as_png(self):
                buf = io.BytesIO()
                Image.new('1', (1, 1)).save(buf, format='png')
                return buf.getvalue()

            def get(self, v):
                self.current_url = v
                return v

        return dummydriver()
