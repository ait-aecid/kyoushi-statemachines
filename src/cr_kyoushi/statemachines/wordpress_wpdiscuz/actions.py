import random
import re

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
    WaitForScrollFinish,
    driver_wait,
    scroll_to,
    slow_type,
    wait_for_page_load,
)
from .context import Context
from .wait import (
    CheckCommentEditor,
    CheckCommentSubmit,
    CheckCommentWriter,
    CheckVoted,
    check_comment_action_failed,
    check_comment_submitted,
    check_is_logged_in,
    check_post_page,
    check_post_rated,
)


class RatePost:
    def __init__(self, min_rating: int = 1, max_rating: int = 5):
        self.min_rating: int = min_rating
        self.max_rating: int = max_rating

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        driver: webdriver.Remote = context.driver
        post_info = context.wpdiscuz.post

        if check_post_page(driver):
            if not check_post_rated(driver):
                # get random rating
                post_info.rating = random.randint(self.min_rating, self.max_rating)

                # set log context
                log = log.bind(wordpress_post=post_info)

                rating_div = driver.find_element_by_id("wpd-post-rating")

                rating_star = rating_div.find_element_by_xpath(
                    f".//div[@class='wpd-rating-stars']/*[name()='svg' and position()={post_info.rating}]"
                )
                rating_starts = rating_div.find_element_by_xpath(
                    f".//div[@class='wpd-rate-starts']/*[name()='svg' and position()={post_info.rating}]"
                )

                log.info("Rating post")
                with wait_for_page_load(driver):
                    # scroll to rating star so we can click it
                    scroll_to(driver, rating_div, options_block="center")

                    ActionChains(driver).move_to_element(rating_star).click(
                        rating_starts
                    ).perform()

                driver_wait(driver, check_post_page)
                log.info("Rated post")
            else:
                log.warning("Post already rated")
        else:
            log.error(
                "Invalid action for current page",
                horde_action="rate_post",
                current_page=driver.current_url,
            )


def get_comments_by_others(driver: webdriver.Remote, author: str) -> List[WebElement]:
    """Get all comment elements other then those by the given author.

    Args:
        driver: The webdriver instance
        author: The author whos comments should be excluded

    Returns:
        The comment web elements
    """
    return driver.find_elements_by_xpath(
        "//div[starts-with(@id,'wpd-comm-') and div[div[starts-with(@id,'comment-') and "
        f"div[@class='wpd-comment-header' and div[not(contains(text(),'{author}')) and "
        "contains(@class,'wpd-comment-author')]]]]]"
    )


def _comment_is_max_level(comment_class: str, max_level: int) -> bool:
    level_regex = r".*wpd_comment_level-(\d*).*"
    match = re.match(level_regex, comment_class)
    if match is not None and int(match.group(1)) <= max_level:
        return True

    return False


def get_comments(
    driver: webdriver.Remote,
    author: str,
    max_level: Optional[int] = None,
) -> List[WebElement]:
    """Get all comment elements other then those by the given author.

    You can also optional limit the returned comments to a certain max level.

    Args:
        driver: The webdriver instance
        author: The author whos comments should be excluded

    Returns:
        The comment web elements
    """
    comments = get_comments_by_others(driver, author)
    if max_level is not None:
        return [
            comment
            for comment in comments
            if _comment_is_max_level(comment.get_attribute("class"), max_level)
        ]
    return comments


def get_comments_not_voted(driver: webdriver.Remote, author: str) -> List[WebElement]:
    """Get all comment elements that the author has not voted on.

    !!! Note
        It is not possible to vote on your own comments.

    Args:
        driver: The webdriver instance
        author: The author whos comments should be excluded

    Returns:
        List[WebElement]: [description]
    """
    return driver.find_elements_by_xpath(
        # comments by other people
        "//div[starts-with(@id,'wpd-comm-') and div[div[starts-with(@id,'comment-') and "
        f"div[@class='wpd-comment-header' and div[not(contains(text(),'{author}')) and "
        "contains(@class,'wpd-comment-author')]] and "
        # that the user has not voted on yet
        "div[contains(@class,'wpd-comment-footer') and div[@class='wpd-vote' and not("
        # not up voted
        "div[contains(@class, 'wpd-vote-up') and contains(@class, 'wpd-up')] or "
        # or down voted
        "div[contains(@class, 'wpd-vote-down') and contains(@class, 'wpd-down')] )]]]]]"
    )


def _get_comment_ids(comment: WebElement) -> Tuple[str, str]:
    """Parses a comment div and retrieves the parent_cid and the cid.

    Args:
        comment: The comment div web element (id='wpd-comm-<cid>_<parrent_cid>')

    Returns:
        A tuple of the form (parrent_cid, cid)
    """
    comment_ids = comment.get_attribute("id").replace("wpd-comm-", "").split("_")
    # (parent_cid, cid)
    return (comment_ids[1], comment_ids[0])


class VoteComment:
    """Vote comment action up or down votes a random comment.

    Comments posted by the author are excluded.
    """

    def __init__(self, up_vote: bool = True):
        """
        Args:
            up_vote. If the vote should be an up or down vote.
        """
        self.up_vote: bool = up_vote

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        driver: webdriver.Remote = context.driver
        post_info = context.wpdiscuz.post
        comment_info = context.wpdiscuz.comment
        # clear comment context
        comment_info.clear()
        author = context.wpdiscuz.author

        # bind post and comment info to logging
        log = log.bind(wordpress_post=post_info, wordpress_comment=comment_info)

        if check_post_page(driver):
            comments = get_comments_not_voted(driver, author)

            if len(comments) > 0:
                comment = random.choice(comments)

                comment_info.parent_cid, comment_info.cid = _get_comment_ids(comment)
                comment_info.up_vote = self.up_vote

                vote_type = "wpd-vote-up" if self.up_vote else "wpd-vote-down"
                vote_icon = comment.find_element_by_xpath(
                    f".//div[@class='wpd-vote']/div[contains(@class,'{vote_type}')]"
                )

                log.info("Voting on comment")
                # ensure vote icon is in view
                scroll_to(driver, vote_icon, options_block="center")
                vote_icon.click()

                # wait for vote to register
                driver_wait(
                    driver,
                    CheckVoted(comment_info.cid, up_vote=self.up_vote),
                )

                if check_comment_action_failed(driver):
                    log.info("Failed to vote on comment")
                else:
                    log.info("Voted on comment")

            else:
                log.warning("No comments to vote on")
        else:
            log.error(
                "Invalid action for current page",
                horde_action="vote_comment",
                current_page=driver.current_url,
            )


def new_comment(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    driver: webdriver.Remote = context.driver
    post_info = context.wpdiscuz.post
    comment_info = context.wpdiscuz.comment
    # clear comment context
    comment_info.clear()

    # bind post and comment info to logging
    log = log.bind(wordpress_post=post_info, wordpress_comment=comment_info)

    if check_post_page(driver):
        new_div = driver.find_element_by_id("wpd-editor-0_0")
        log.info("Starting new comment")

        # scroll to comment area
        scroll_to(driver, new_div, options_block="center")

        # click into text field to make submit button & co appear
        new_div.find_element_by_class_name("ql-editor").click()
        driver_wait(driver, CheckCommentSubmit())
    else:
        log.error(
            "Invalid action for current page",
            horde_action="new_comment",
            current_page=driver.current_url,
        )


class ReplyComment:
    """Reply comment action initiates the process of replying to a comment.

    Comments posted by the author are can never be replied to.
    """

    def __init__(self, max_level: Optional[int] = None):
        """
        Args:
            max_level. The maximum comment depth level to reply to
        """
        self.max_level: Optional[int] = max_level

    def __call__(
        self,
        log: BoundLogger,
        current_state: str,
        context: Context,
        target: Optional[str],
    ):
        driver: webdriver.Remote = context.driver
        post_info = context.wpdiscuz.post
        comment_info = context.wpdiscuz.comment
        # clear comment context
        comment_info.clear()
        comment_info.author = context.wpdiscuz.author

        # bind post and comment info to logging
        log = log.bind(wordpress_post=post_info, wordpress_comment=comment_info)

        if check_post_page(driver):
            comments = get_comments(driver, comment_info.author, self.max_level)

            if len(comments) > 0:
                comment = random.choice(comments)

                # set id info of selected comment
                comment_info.parent_cid, comment_info.cid = _get_comment_ids(comment)

                reply_button = comment.find_element_by_class_name("wpd-reply-button")

                log.info("Starting reply comment")
                # scroll to reply button for comment
                scroll_to(driver, reply_button, options_block="center")

                reply_button.click()
                # wait for edit form to appear
                driver_wait(
                    driver,
                    CheckCommentEditor(comment_info.parent_cid, comment_info.cid),
                )

                reply_div = driver.find_element_by_id(
                    f"wpd-editor-{comment_info.cid}_{comment_info.parent_cid}"
                )

                # click into text field to make submit button & co appear
                reply_div.find_element_by_class_name("ql-editor").click()
                driver_wait(
                    driver,
                    CheckCommentSubmit(comment_info.parent_cid, comment_info.cid),
                )

            else:
                log.warning("No comments to reply to")
        else:
            log.error(
                "Invalid action for current page",
                horde_action="reply_comment",
                current_page=driver.current_url,
            )


def write_comment(
    log: BoundLogger,
    current_state: str,
    context: Context,
    target: Optional[str],
):
    """Write comment action writes a wpdiscuz comment.

    This could be a reply to a comment or a new top level comment.
    """
    driver: webdriver.Remote = context.driver
    post_info = context.wpdiscuz.post
    comment_info = context.wpdiscuz.comment

    # bind post and comment info to logging
    log = log.bind(wordpress_post=post_info, wordpress_comment=comment_info)

    parent_cid = comment_info.parent_cid
    cid = comment_info.cid

    # when writing a new comment we do not have ids
    # wpdiscuz marks the editor for this with the fake ids 0_0
    if parent_cid is None or cid is None:
        parent_cid = "0"
        cid = "0"

    if check_post_page(driver) and CheckCommentWriter(parent_cid, cid):
        editor_div = driver.find_element_by_id(f"wpd-editor-{cid}_{parent_cid}")
        comment_info.author = context.wpdiscuz.author
        comment_info.email = context.wpdiscuz.email
        comment_info.text = " ".join(context.fake.sentences(random.randint(1, 2)))

        input_text = editor_div.find_element_by_class_name("ql-editor")

        if check_is_logged_in(driver):
            # when the user is logged in set the author name
            # to the logged in user just in case
            comment_info.author = driver.find_element_by_xpath(
                "//div[@id='wpdcom']//div[contains(@class,'wpd-login')]/a[contains(@href,'/author/')]"
            ).text
            # also when logged in we don't submit an email address
            comment_info.email = None
        else:
            # when we are not logged in we will have to supply name + email
            input_name = driver.find_element_by_id(f"wc_name-{cid}_{parent_cid}")
            input_email = driver.find_element_by_id(f"wc_email-{cid}_{parent_cid}")

        log.info("Writing comment")

        input_text.clear()
        slow_type(input_text, comment_info.text)

        if not check_is_logged_in(driver):
            assert comment_info.author is not None
            assert comment_info.email is not None

            input_name.clear()
            slow_type(input_name, comment_info.author)

            input_email.clear()
            slow_type(input_email, comment_info.email)

        log.info("Submitting comment")

        # after submitting a comment wpdiscuz automatically scrolls to it
        # so we save current y post to be able to wait for change later
        y_pos = driver.execute_script("return window.pageYOffset")
        driver.find_element_by_id(f"wpd-field-submit-{cid}_{parent_cid}").click()

        # ensure comment submitted
        driver_wait(driver, check_comment_submitted)

        if check_comment_action_failed(driver):
            log.info("Failed to submit comment")
        else:
            log.info("Submitted comment")
            # if the submit was a success we have to wait for the auto scroll
            WaitForScrollFinish(driver, y_pos=y_pos).wait()
    else:
        log.error(
            "Invalid action for current page",
            horde_action="write_comment",
            current_page=driver.current_url,
        )
