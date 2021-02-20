"""
A collection of helper functions used to create the various sub activities of the OwnCloud user activity.
"""

from typing import (
    Optional,
    Tuple,
)

from cr_kyoushi.simulation.transitions import (
    DelayedTransition,
    Transition,
    noop,
)

from ..core.config import IdleConfig
from . import (
    actions,
    config,
    states,
)


def get_ssh_activity(
    idle: IdleConfig,
    user: config.SSHUserConfig,
    connected_config: config.ConnectedConfig,
    sudo_config: config.SudoDialogConfig,
    root: str = "selecting_activity",
    selected_server: str = "selected_server",
    connected: str = "connected",
    executing_chain: str = "executing_chain",
    sudo_check: str = "sudo_check",
    sudo_dialog: str = "sudo_dialog",
    # transitions
    select_server: str = "select_ssh_server",
    ssh_connect: str = "ssh_connect",
    ssh_disconnect: str = "ssh_disconnect",
    select_chain: str = "select_command_chain",
    command_finished: str = "command_finished",
    exec_command: str = "exec_command",
    enter_sudo_password: str = "enter_sudo_password",
    fail_sudo_password: str = "fail_sudo_password",
    fail_sudo: str = "fail_sudo",
    name_prefix: Optional[str] = None,
) -> Tuple[
    # transitions
    Transition,
    # states
    states.SelectedServer,
    states.Connected,
    states.ExecutingCommandChain,
    states.SudoDialogCheck,
    states.SudoDialog,
]:
    """Creates the SSH user activity and its underlying states and transitions.

    It is possible to assign different names to the states and transitions via the
    function arguments.

    Returns:
        The SSH user activity states and the initial transition as tuple of the form:
        (
            select_ssh_server,
            selected_server,
            connected,
            executing_chain,
            sudo_check,
            sudo_dialog,
        )
    """
    if name_prefix:
        target_selected_server = f"{name_prefix}_{selected_server}"
        target_connected = f"{name_prefix}_{connected}"
        target_executing_chain = f"{name_prefix}_{executing_chain}"
        target_sudo_check = f"{name_prefix}_{sudo_check}"
        target_sudo_dialog = f"{name_prefix}_{sudo_dialog}"
    else:
        target_selected_server = selected_server
        target_connected = connected
        target_executing_chain = executing_chain
        target_sudo_check = sudo_check
        target_sudo_dialog = sudo_dialog

    host_cfgs = config.get_hosts(user)

    t_select_server = Transition(
        transition_function=actions.SelectHost(user.hosts, host_cfgs),
        name=select_server,
        target=target_selected_server,
        name_prefix=name_prefix,
    )

    t_connect = DelayedTransition(
        transition_function=actions.connect,
        name=ssh_connect,
        target=target_connected,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    t_disconnect = DelayedTransition(
        transition_function=actions.disconnect,
        name=ssh_disconnect,
        target=root,
        delay_after=idle.medium,
        name_prefix=name_prefix,
    )

    t_select_chain = Transition(
        transition_function=actions.select_chain,
        name=select_chain,
        target=target_executing_chain,
        name_prefix=name_prefix,
    )

    t_exec_cmd = Transition(
        transition_function=actions.execute_command,
        name=exec_command,
        target=target_sudo_check,
        name_prefix=name_prefix,
    )

    t_finished = DelayedTransition(
        transition_function=noop,
        name=command_finished,
        target=target_connected,
        delay_after=idle.small,
        name_prefix=name_prefix,
    )

    # each command has their own idle time configured
    # so we don't want to use a delayed transition here
    t_enter_password = Transition(
        transition_function=actions.enter_sudo_password,
        name=enter_sudo_password,
        target=target_executing_chain,
        name_prefix=name_prefix,
    )

    t_fail_password = DelayedTransition(
        transition_function=actions.fail_sudo,
        name=fail_sudo_password,
        target=target_sudo_check,
        delay_after=idle.tiny,
        name_prefix=name_prefix,
    )

    t_fail_sudo = DelayedTransition(
        transition_function=actions.fail_sudo,
        name=fail_sudo,
        target=target_executing_chain,
        delay_after=idle.tiny,
        name_prefix=name_prefix,
    )

    # states

    s_selected_server = states.SelectedServer(
        name=selected_server,
        transition=t_connect,
        name_prefix=name_prefix,
    )

    s_connected = states.Connected(
        name=connected,
        select_chain=t_select_chain,
        disconnect=t_disconnect,
        select_chain_weight=connected_config.select_chain,
        disconnect_weight=connected_config.disconnect,
        disconnect_increase=connected_config.extra.disconnect_increase,
        name_prefix=name_prefix,
    )

    s_executing_chain = states.ExecutingCommandChain(
        name=executing_chain,
        execute_command=t_exec_cmd,
        finished=t_finished,
        name_prefix=name_prefix,
    )

    s_sudo_check = states.SudoDialogCheck(
        name=sudo_check,
        exec_cmd_chain=target_executing_chain,
        sudo_dialog=target_sudo_dialog,
        name_prefix=name_prefix,
    )

    s_sudo_dialog = states.SudoDialog(
        name=sudo_dialog,
        enter_password=t_enter_password,
        fail_password=t_fail_password,
        fail_escalation=t_fail_sudo,
        enter_password_weight=sudo_config.enter_password,
        fail_password_weight=sudo_config.fail,
        fail_increase=sudo_config.extra.fail_increase,
        name_prefix=name_prefix,
    )

    return (
        # transitions
        t_select_server,
        # states
        s_selected_server,
        s_connected,
        s_executing_chain,
        s_sudo_check,
        s_sudo_dialog,
    )
