import random

from typing import (
    List,
    Optional,
    Tuple,
)

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webelement import WebElement
from structlog.stdlib import BoundLogger

from ..core.selenium import (
    driver_wait,
    scroll_to,
    slow_type,
)
from ..core.util import get_title
from .context import (
    Context,
    WordpressCommentReplyInfo,
    WordpressEditorContext,
    WordpressPostInfo,
)
from .wait import (
    check_admin_comments,
    check_admin_menu,
    check_admin_posts,
    check_comment_reply_editor,
    check_logged_out,
    check_login_error,
    check_login_page,
    check_post_editor,
    check_post_editor_page,
    check_post_welcome_guide,
    check_publish_button_active,
    check_publish_init_button_active,
    check_published_panel,
    check_submitted_comment_reply,
)


def login_to_wordpress(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    driver: webdriver.Remote = context.driver
    user: WordpressEditorContext = context.wp_editor
    if check_login_page(driver):
        user_input = driver.find_element_by_id("user_login")
        password_input = driver.find_element_by_id("user_pass")

        # bind login creds to log context
        log = log.bind(wp_user=user.username, wp_password=user.password)

        user_input.clear()
        slow_type(user_input, user.username)

        password_input.clear()
        slow_type(password_input, user.password)

        log.info("Logging into wordpress")

        driver.find_element_by_id("wp-submit").click()
        driver_wait(driver, check_admin_menu)

        log.info("Logged into wordpress")
    else:
        log.error(
            "Invalid action for current page",
            wp_editor_action="login",
            current_page=driver.current_url,
        )


def logout_of_wordpress(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    driver: webdriver.Remote = context.driver
    if check_admin_menu(driver):
        logout_link = driver.find_element_by_xpath(
            "//li[@id='wp-admin-bar-logout']/a"
        ).get_attribute("href")

        log.info("Logging out of wordpress")

        driver.get(logout_link)
        driver_wait(driver, check_logged_out)

        log.info("Logged out of wordpress")
    else:
        log.error(
            "Invalid action for current page",
            wp_editor_action="logout",
            current_page=driver.current_url,
        )


def fail_login_to_wordpress(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    driver: webdriver.Remote = context.driver
    user: WordpressEditorContext = context.wp_editor
    if check_login_page(driver):
        user_input = driver.find_element_by_id("user_login")
        password_input = driver.find_element_by_id("user_pass")

        incorrect_password = context.fake.pystr(max_chars=len(user.password))
        # bind login creds to log context
        log = log.bind(wp_user=user.username, wp_password=incorrect_password)

        user_input.clear()
        slow_type(user_input, user.username)

        password_input.clear()
        slow_type(password_input, incorrect_password)

        log.info("Failing login into wordpress")

        driver.find_element_by_id("wp-submit").click()
        driver_wait(driver, check_login_error)

        log.info("Failed login into wordpress")
    else:
        log.error(
            "Invalid action for current page",
            wp_editor_action="login",
            current_page=driver.current_url,
        )


def new_post(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    driver: webdriver.Remote = context.driver
    if check_admin_posts(driver):
        # reset post context
        context.wp_editor.post.clear()

        add_new_link = driver.find_element_by_xpath(
            "//div[@id='wpbody']//a[contains(@class,'page-title-action') and text()='Add New']"
        ).get_attribute("href")

        log.info("Start new post")
        driver.get(add_new_link)
        driver_wait(driver, check_post_editor_page)
        log.info("Started new post")

        if check_post_welcome_guide:
            guide_close = driver.find_element_by_xpath(
                "//div[contains(@class, 'edit-post-welcome-guide')]//button[contains(@class, 'components-button') and @aria-label='Close dialog']"
            )
            log.info("Dismissing welcome guide")
            guide_close.click()
            driver_wait(driver, check_post_editor)
            log.info("Dismissed welcome guide")
    else:
        log.error(
            "Invalid action for current page",
            wp_editor_action="new_post",
            current_page=driver.current_url,
        )


def write_post(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    driver: webdriver.Remote = context.driver
    post: WordpressPostInfo = context.wp_editor.post

    if check_post_editor(driver):
        # bind post to log context
        log = log.bind(wp_post=post)

        title_input = driver.find_element_by_id("post-title-0")

        post.title = get_title(context.fake)
        post.content = [
            context.fake.paragraph(
                nb_sentences=random.randint(3, 6),
            )
            for _ in range(0, random.randint(1, 4))
        ]
        log.info("Writing wordpress post")

        slow_type(title_input, post.title)

        driver.find_element_by_xpath(
            "//div[@id='editor']//div[contains(@class, 'is-root-container')]//textarea"
        ).click()

        for paragraph in post.content:
            text_input = driver.find_element_by_xpath(
                "//div[@id='editor']//div[contains(@class, 'is-root-container')]//p[@data-title='Paragraph'][last()]"
            )
            slow_type(text_input, paragraph + "\n")

        driver_wait(driver, check_publish_init_button_active)
        log.info("Wrote wordpress post")
    else:
        log.error(
            "Invalid action for current page",
            wp_editor_action="write_post",
            current_page=driver.current_url,
        )


def publish_post(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    driver: webdriver.Remote = context.driver
    post: WordpressPostInfo = context.wp_editor.post

    if check_publish_init_button_active(driver):
        # bind post to log context
        log = log.bind(wp_post=post)

        log.info("Publishing post")
        driver.find_element_by_xpath(
            "//div[@class='edit-post-header']//button[contains(@class,'editor-post-publish-button')]"
        ).click()
        driver_wait(driver, check_publish_button_active)

        driver.find_element_by_xpath(
            "//div[@class='editor-post-publish-panel']//button[contains(@class,'editor-post-publish-button')]"
        ).click()
        driver_wait(driver, check_published_panel)

    else:
        log.error(
            "Invalid action for current page",
            wp_editor_action="publish_post",
            current_page=driver.current_url,
        )


def get_comments_by_others(
    driver: webdriver.Remote,
    username: str,
    only_guests: bool = True,
) -> List[WebElement]:
    """Gets all comment table row elements for comments by authors other than the user.

    Optionally returns only comments by guests.

    Args:
        driver: The webdriver instance
        username: The username of the user whos comments to exclude
        only_guests: If only guest comments should be returned or not

    Returns:
        A list of comment table row web elements
    """
    extra_condition = f"not(contains(@class, 'comment-author-{username}'))"
    if only_guests:
        extra_condition = "not(contains(@class, 'byuser')) and " + extra_condition

    return driver.find_elements_by_xpath(
        f"//tbody[@id='the-comment-list']/tr[starts-with(@id, 'comment-') and {extra_condition}]"
    )


def get_comment_ids(comment: WebElement) -> Tuple[str, str]:
    """Retrieves the comment and post id from a comment table row element.

    Args:
        comment: The table row element

    Returns:
        The ids in the format (cid, pid)
    """
    reply_button = comment.find_element_by_xpath(".//button[@data-action='replyto']")
    cid = reply_button.get_attribute("data-comment-id")
    pid = reply_button.get_attribute("data-post-id")
    return (cid, pid)


class ReplyToComment:
    def __init__(self, only_guests: bool = True):
        self.only_guests: bool = only_guests

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        driver: webdriver.Remote = context.driver
        reply: WordpressCommentReplyInfo = context.wp_editor.comment_reply

        if check_admin_comments(driver):
            comments = get_comments_by_others(
                driver,
                context.wp_editor.username,
                only_guests=self.only_guests,
            )
            if len(comments) > 0:
                # clear reply context
                reply.clear()

                # bind reply to log context
                log = log.bind(wp_comment_reply=reply)

                comment = random.choice(comments)
                reply_button = comment.find_element_by_xpath(
                    ".//button[@data-action='replyto']"
                )

                # get ids and create random text
                (reply.cid, reply.pid) = get_comment_ids(comment)

                log.info("Starting comment reply")
                scroll_to(driver, comment)
                action = ActionChains(driver)
                action.move_to_element(comment).move_to_element(reply_button)
                action.click(reply_button).perform()

                # wait for reply textarea to be available
                driver_wait(driver, check_comment_reply_editor)
                log.info("Started comment reply")
            else:
                log.warn("No comments to reply to")

        else:
            log.error(
                "Invalid action for current page",
                wp_editor_action="reply_to_comment",
                current_page=driver.current_url,
            )


def write_comment_reply(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    driver: webdriver.Remote = context.driver
    reply: WordpressCommentReplyInfo = context.wp_editor.comment_reply

    if check_comment_reply_editor(driver):
        # bind reply to log context
        log = log.bind(wp_comment_reply=reply)

        reply.content = " ".join(context.fake.sentences(random.randint(1, 2)))

        reply_input = driver.find_element_by_id("replycontent")
        reply_button = driver.find_element_by_xpath(
            "//div[@id='replysubmit']//button[contains(@class,'save')]"
        )
        slow_type(reply_input, reply.content)
        log.info("Submitting comment reply")
        reply_button.click()
        driver_wait(driver, check_submitted_comment_reply)
        log.info("Submitted comment reply ")
    else:
        log.error(
            "Invalid action for current page",
            wp_editor_action="write_comment_reply",
            current_page=driver.current_url,
        )
