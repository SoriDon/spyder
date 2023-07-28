# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Debugger Main Plugin Widget.
"""

# Third party imports
from qtpy.QtCore import Signal, Slot

# Local imports
from spyder.api.shellconnect.main_widget import ShellConnectMainWidget
from spyder.api.translations import _
from spyder.config.manager import CONF
from spyder.config.gui import get_color_scheme
from spyder.plugins.debugger.widgets.framesbrowser import (
    FramesBrowser, FramesBrowserState)


# =============================================================================
# ---- Constants
# =============================================================================
class DebuggerWidgetActions:
    # Triggers
    Search = 'search'
    Inspect = 'inspect'
    EnterDebug = 'enter_debug'
    Next = "next"
    Continue = "continue"
    Step = "step"
    Return = "return"
    Stop = "stop"
    GotoCursor = "go to editor"

    # Toggles
    ToggleExcludeInternal = 'toggle_exclude_internal_action'
    ToggleCaptureLocals = 'toggle_capture_locals_action'
    ToggleLocalsOnClick = 'toggle_show_locals_on_click_action'


class DebuggerBreakpointActions:
    ToggleBreakpoint = 'toggle breakpoint'
    ToggleConditionalBreakpoint = 'toggle conditional breakpoint'
    ClearAllBreakpoints = 'clear all breakpoints'


class DebuggerWidgetOptionsMenuSections:
    Display = 'excludes_section'
    Highlight = 'highlight_section'


class DebuggerWidgetMainToolBarSections:
    Main = 'main_section'


class DebuggerWidgetMenus:
    EmptyContextMenu = 'empty'
    PopulatedContextMenu = 'populated'


class DebuggerContextMenuSections:
    Locals = 'locals_section'


class DebuggerContextMenuActions:
    ViewLocalsAction = 'view_locals_action'


# =============================================================================
# ---- Widgets
# =============================================================================
class DebuggerWidget(ShellConnectMainWidget):

    # PluginMainWidget class constants
    ENABLE_SPINNER = True

    # Signals
    sig_edit_goto = Signal(str, int, str)
    """
    This signal will request to open a file in a given row and column
    using a code editor.

    Parameters
    ----------
    path: str
        Path to file.
    row: int
        Cursor starting row position.
    word: str
        Word to select on given row.
    """

    sig_show_namespace = Signal(dict, object)
    """
    Show the namespace

    Parameters
    ----------
    namespace: dict
        A namespace view created by spyder_kernels
    shellwidget: object
        The shellwidget the request originated from
    """

    sig_breakpoints_saved = Signal()
    """Breakpoints have been saved"""

    sig_toggle_breakpoints = Signal()
    """Add or remove a breakpoint on the current line."""

    sig_toggle_conditional_breakpoints = Signal()
    """Add or remove a conditional breakpoint on the current line."""

    sig_clear_all_breakpoints = Signal()
    """Clear all breakpoints in all files."""

    sig_pdb_state_changed = Signal(bool)
    """
    This signal is emitted every time a Pdb interaction happens.

    Parameters
    ----------
    pdb_state: bool
        Whether the debugger is waiting for input
    """

    sig_load_pdb_file = Signal(str, int)
    """
    This signal is emitted when Pdb reaches a new line.

    Parameters
    ----------
    filename: str
        The filename the debugger stepped in
    line_number: int
        The line number the debugger stepped in
    """

    def __init__(self, name=None, plugin=None, parent=None):
        super().__init__(name, plugin, parent)

        # Widgets
        self.context_menu = None
        self.empty_context_menu = None

    # ---- PluginMainWidget API
    # ------------------------------------------------------------------------
    def get_title(self):
        return _('Debugger')

    def get_focus_widget(self):
        return self.current_widget()

    def setup(self):
        """Setup the widget."""
        # ---- Options menu actions
        exclude_internal_action = self.create_action(
            DebuggerWidgetActions.ToggleExcludeInternal,
            text=_("Exclude internal frames when inspecting execution"),
            tip=_("Exclude frames that are not part of the user code"),
            toggled=True,
            option='exclude_internal',
        )

        capture_locals_action = self.create_action(
            DebuggerWidgetActions.ToggleCaptureLocals,
            text=_("Capture locals when inspecting execution"),
            tip=_("Capture the variables in the Variable Explorer"),
            toggled=True,
            option='capture_locals',
        )

        show_locals_on_click_action = self.create_action(
            DebuggerWidgetActions.ToggleLocalsOnClick,
            text=_("Show selected frame locals from inspection "
                   "in the Variable Explorer"),
            tip=_("Show frame locals in the Variable explorer when selected."),
            toggled=True,
            option='show_locals_on_click',
        )

        # ---- Toolbar actions
        search_action = self.create_action(
            DebuggerWidgetActions.Search,
            text=_("Search frames"),
            icon=self.create_icon('find'),
            toggled=self.toggle_finder,
            register_shortcut=True
        )

        inspect_action = self.create_action(
            DebuggerWidgetActions.Inspect,
            text=_("Inspect execution"),
            icon=self.create_icon('show'),
            triggered=self.capture_frames,
            register_shortcut=True,
        )

        enter_debug_action = self.create_action(
            DebuggerWidgetActions.EnterDebug,
            text=_("Interrupt execution and enter debugger"),
            icon=self.create_icon('enter_debug'),
            triggered=self.enter_debug,
            register_shortcut=True,
        )

        next_action = self.create_action(
            DebuggerWidgetActions.Next,
            text=_("Execute current line"),
            icon=self.create_icon('arrow-step-over'),
            triggered=lambda: self.debug_command("next"),
            register_shortcut=True
        )

        continue_action = self.create_action(
            DebuggerWidgetActions.Continue,
            text=_("Continue execution until next breakpoint"),
            icon=self.create_icon('arrow-continue'),
            triggered=lambda: self.debug_command("continue"),
            register_shortcut=True
        )

        step_action = self.create_action(
            DebuggerWidgetActions.Step,
            text=_("Step into function or method"),
            icon=self.create_icon('arrow-step-in'),
            triggered=lambda: self.debug_command("step"),
            register_shortcut=True
        )

        return_action = self.create_action(
            DebuggerWidgetActions.Return,
            text=_("Execute until function or method returns"),
            icon=self.create_icon('arrow-step-out'),
            triggered=lambda: self.debug_command("return"),
            register_shortcut=True
        )

        stop_action = self.create_action(
            DebuggerWidgetActions.Stop,
            text=_("Stop debugging"),
            icon=self.create_icon('stop_debug'),
            triggered=self.stop_debugging,
            register_shortcut=True
        )

        goto_cursor_action = self.create_action(
            DebuggerWidgetActions.GotoCursor,
            text=_("Show in the editor the file and line where the debugger "
                   "is placed"),
            icon=self.create_icon('fromcursor'),
            triggered=self.goto_current_step,
            register_shortcut=True
        )

        self.create_action(
            DebuggerBreakpointActions.ToggleBreakpoint,
            text=_("Set/Clear breakpoint"),
            tip=_("Set/Clear breakpoint"),
            icon=self.create_icon('breakpoint_big'),
            triggered=self.sig_toggle_breakpoints,
            register_shortcut=True,
        )

        self.create_action(
            DebuggerBreakpointActions.ToggleConditionalBreakpoint,
            text=_("Set/Edit conditional breakpoint"),
            tip=_("Set/Edit conditional breakpoint"),
            icon=self.create_icon('breakpoint_cond_big'),
            triggered=self.sig_toggle_conditional_breakpoints,
            register_shortcut=True,
        )

        self.create_action(
            DebuggerBreakpointActions.ClearAllBreakpoints,
            text=_("Clear breakpoints in all files"),
            tip=_("Clear breakpoints in all files"),
            triggered=self.sig_clear_all_breakpoints
        )

        # ---- Context menu actions
        self.view_locals_action = self.create_action(
            DebuggerContextMenuActions.ViewLocalsAction,
            _("View variables with the Variable Explorer"),
            icon=self.create_icon('outline_explorer'),
            triggered=self.view_item_locals
        )

        # Options menu
        options_menu = self.get_options_menu()
        for item in [
                exclude_internal_action,
                capture_locals_action,
                show_locals_on_click_action]:
            self.add_item_to_menu(
                item,
                menu=options_menu,
                section=DebuggerWidgetOptionsMenuSections.Display,
            )

        # Main toolbar
        main_toolbar = self.get_main_toolbar()
        for item in [next_action,
                     continue_action,
                     step_action,
                     return_action,
                     stop_action,
                     goto_cursor_action,
                     enter_debug_action,
                     inspect_action,
                     search_action]:
            self.add_item_to_toolbar(
                item,
                toolbar=main_toolbar,
                section=DebuggerWidgetMainToolBarSections.Main,
            )

        # ---- Context menu to show when there are frames present
        self.context_menu = self.create_menu(
            DebuggerWidgetMenus.PopulatedContextMenu)
        for item in [self.view_locals_action, inspect_action]:
            self.add_item_to_menu(
                item,
                menu=self.context_menu,
                section=DebuggerContextMenuSections.Locals,
            )

        # ---- Context menu when the debugger is empty
        self.empty_context_menu = self.create_menu(
            DebuggerWidgetMenus.EmptyContextMenu)
        for item in [inspect_action]:
            self.add_item_to_menu(
                item,
                menu=self.empty_context_menu,
                section=DebuggerContextMenuSections.Locals,
            )

    def update_actions(self):
        """Update actions."""
        search_action = self.get_action(DebuggerWidgetActions.Search)
        enter_debug_action = self.get_action(
            DebuggerWidgetActions.EnterDebug)
        inspect_action = self.get_action(
            DebuggerWidgetActions.Inspect)

        widget = self.current_widget()
        if self.is_current_widget_empty() or widget is None:
            search_action.setEnabled(False)
            show_enter_debugger = False
            executing = False
            is_inspecting = False
            pdb_prompt = False
        else:
            search_action.setEnabled(True)
            search_action.setChecked(widget.finder_is_visible())
            post_mortem = widget.state == FramesBrowserState.Error
            sw = widget.shellwidget
            executing = sw._executing
            show_enter_debugger = post_mortem or executing
            is_inspecting = widget.state == FramesBrowserState.Inspect
            pdb_prompt = sw.is_waiting_pdb_input()

        enter_debug_action.setEnabled(show_enter_debugger)
        inspect_action.setEnabled(executing)
        self.context_menu.setEnabled(is_inspecting)

        for action_name in [
                DebuggerWidgetActions.Next,
                DebuggerWidgetActions.Continue,
                DebuggerWidgetActions.Step,
                DebuggerWidgetActions.Return,
                DebuggerWidgetActions.Stop,
                DebuggerWidgetActions.GotoCursor]:
            action = self.get_action(action_name)
            action.setEnabled(pdb_prompt)

    # ---- ShellConnectMainWidget API
    # ------------------------------------------------------------------------
    def create_new_widget(self, shellwidget):
        """Create a new widget."""
        color_scheme = get_color_scheme(
            CONF.get('appearance', 'selected'))
        widget = FramesBrowser(
            self,
            shellwidget=shellwidget,
            color_scheme=color_scheme
        )

        widget.sig_edit_goto.connect(self.sig_edit_goto)
        widget.sig_hide_finder_requested.connect(self.hide_finder)
        widget.sig_update_actions_requested.connect(self.update_actions)

        widget.sig_show_namespace.connect(self.sig_show_namespace)
        shellwidget.sig_prompt_ready.connect(widget.clear_if_needed)
        shellwidget.sig_pdb_prompt_ready.connect(widget.clear_if_needed)

        shellwidget.sig_prompt_ready.connect(self.update_actions)
        shellwidget.sig_pdb_prompt_ready.connect(self.update_actions)
        shellwidget.executing.connect(self.update_actions)

        shellwidget.kernel_handler.kernel_comm.register_call_handler(
            "show_traceback", widget.show_exception)
        shellwidget.sig_pdb_stack.connect(widget.set_from_pdb)
        shellwidget.sig_config_spyder_kernel.connect(
            widget.on_config_kernel)

        widget.setup()
        widget.set_context_menu(
            self.context_menu,
            self.empty_context_menu
        )

        widget.results_browser.view_locals_action = self.view_locals_action
        self.sig_breakpoints_saved.connect(widget.set_breakpoints)

        shellwidget.sig_pdb_state_changed.connect(self.sig_pdb_state_changed)
        shellwidget.sig_pdb_step.connect(widget.pdb_has_stopped)

        widget.sig_load_pdb_file.connect(self.sig_load_pdb_file)

        return widget

    def switch_widget(self, widget, old_widget):
        """Set the current FramesBrowser."""
        if not self.is_current_widget_empty():
            sw = widget.shellwidget
            state = sw.is_waiting_pdb_input()
            self.sig_pdb_state_changed.emit(state)

    def close_widget(self, widget):
        """Close widget."""
        widget.sig_edit_goto.disconnect(self.sig_edit_goto)
        widget.sig_hide_finder_requested.disconnect(self.hide_finder)
        widget.sig_update_actions_requested.disconnect(self.update_actions)

        shellwidget = widget.shellwidget

        widget.sig_show_namespace.disconnect(self.sig_show_namespace)

        try:
            shellwidget.sig_prompt_ready.disconnect(widget.clear_if_needed)
            shellwidget.sig_prompt_ready.disconnect(self.update_actions)
        except TypeError:
            # disconnect was called elsewhere without argument
            pass

        shellwidget.sig_pdb_prompt_ready.disconnect(widget.clear_if_needed)
        shellwidget.sig_pdb_prompt_ready.disconnect(self.update_actions)
        shellwidget.executing.disconnect(self.update_actions)

        shellwidget.kernel_handler.kernel_comm.unregister_call_handler(
            "show_traceback")
        shellwidget.sig_pdb_stack.disconnect(widget.set_from_pdb)
        shellwidget.sig_config_spyder_kernel.disconnect(
            widget.on_config_kernel)
        widget.on_unconfig_kernel()
        self.sig_breakpoints_saved.disconnect(widget.set_breakpoints)
        shellwidget.sig_pdb_state_changed.disconnect(
            self.sig_pdb_state_changed)

        shellwidget.sig_pdb_step.disconnect(widget.pdb_has_stopped)
        widget.sig_load_pdb_file.disconnect(self.sig_load_pdb_file)

        widget.close()
        widget.setParent(None)

    # ---- Public API
    # ------------------------------------------------------------------------
    def goto_current_step(self):
        """Go to last pdb step."""
        fname, lineno = self.get_pdb_last_step()
        if fname:
            self.sig_load_pdb_file.emit(fname, lineno)

    def print_debug_file_msg(self):
        """Print message in the current console when a file can't be closed."""
        widget = self.current_widget()
        if widget is None:
            return False
        sw = widget.shellwidget
        debug_msg = _('The current file cannot be closed because it is '
                      'in debug mode.')
        sw.append_html_message(debug_msg, before_prompt=True)

    def set_pdb_take_focus(self, take_focus):
        """
        Set whether current Pdb session should take focus when stopping on the
        next call.
        """
        widget = self.current_widget()
        if widget is None or self.is_current_widget_empty():
            return False
        widget.shellwidget._pdb_take_focus = take_focus

    @Slot(bool)
    def toggle_finder(self, checked):
        """Show or hide finder."""
        widget = self.current_widget()
        if widget is None or self.is_current_widget_empty():
            return
        widget.toggle_finder(checked)

    def get_pdb_state(self):
        """Get debugging state of the current console."""
        widget = self.current_widget()
        if widget is None or self.is_current_widget_empty():
            return False
        sw = widget.shellwidget
        if sw is not None:
            return sw.is_waiting_pdb_input()
        return False

    def get_pdb_last_step(self):
        """Get last pdb step of the current console."""
        widget = self.current_widget()
        if widget is None or self.is_current_widget_empty():
            return None, None
        sw = widget.shellwidget
        if sw is not None:
            return sw.get_pdb_last_step()
        return None, None

    @Slot()
    def hide_finder(self):
        """Hide finder."""
        action = self.get_action(DebuggerWidgetActions.Search)
        action.setChecked(False)

    def view_item_locals(self):
        """Request to view item locals."""
        self.current_widget().results_browser.view_item_locals()

    def enter_debug(self):
        """
        Enter the debugger.

        If the shell is executing, interrupt execution and enter debugger.
        If an exception took place, run post mortem.
        """
        widget = self.current_widget()
        if widget is None:
            return

        # Enter the debugger
        sw = widget.shellwidget
        if sw._executing:
            sw.call_kernel(
                interrupt=True, callback=widget.show_pdb_preview
                ).get_current_frames(
                    ignore_internal_threads=True,
                    capture_locals=False)

            sw.call_kernel(interrupt=True).request_pdb_stop()
            return

        if widget.state == FramesBrowserState.Error:
            # Debug the last exception
            sw.execute("%debug")
            return

    def capture_frames(self):
        """Refresh frames table"""
        widget = self.current_widget()
        if widget is None:
            return
        if widget.shellwidget.is_waiting_pdb_input():
            # Disabled while waiting pdb input as the pdb stack is shown
            return
        widget.shellwidget.call_kernel(
            interrupt=True, callback=widget.show_captured_frames
            ).get_current_frames(
                ignore_internal_threads=self.get_conf("exclude_internal"),
                capture_locals=self.get_conf("capture_locals"))

    def stop_debugging(self):
        """Stop debugging"""
        self.sig_unmaximize_plugin_requested.emit()
        widget = self.current_widget()
        if widget is None:
            return
        widget.shellwidget.stop_debugging()

    def debug_command(self, command):
        """Debug actions"""
        self.sig_unmaximize_plugin_requested.emit()
        widget = self.current_widget()
        if widget is None:
            return
        widget.shellwidget.pdb_execute_command(command)
