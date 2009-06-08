# Creates a task-bar icon with balloon tip.  Run from Python.exe to see the
# messages printed.  Right click for balloon tip.  Double click to exit.
# original version of this demo available at http://www.itamarst.org/software/
import win32api, win32con, win32gui

class Taskbar:
    def __init__(self):
        self.visible = 0
        message_map = {
            win32con.WM_DESTROY: self.onDestroy,
            win32con.WM_USER+20 : self.onTaskbarNotify,
            win32con.WM_COMMAND : self.onCommand
        }
        # Register the Window class.
        wc = win32gui.WNDCLASS()
        hinst = wc.hInstance = win32api.GetModuleHandle(None)
        wc.lpszClassName = "PythonTaskbarDemo"
        wc.style = win32con.CS_VREDRAW | win32con.CS_HREDRAW;
        wc.hCursor = win32gui.LoadCursor( 0, win32con.IDC_ARROW )
        wc.hbrBackground = win32con.COLOR_WINDOW
        wc.lpfnWndProc = message_map # could also specify a wndproc.
        classAtom = win32gui.RegisterClass(wc)
        # Create the Window.
        style = win32con.WS_OVERLAPPED | win32con.WS_SYSMENU
        self.hwnd = win32gui.CreateWindow( classAtom, "Taskbar Demo", style, \
                    0, 0, win32con.CW_USEDEFAULT, win32con.CW_USEDEFAULT, \
                    0, 0, hinst, None)
        win32gui.UpdateWindow(self.hwnd)

    def setIcon(self, hicon, tooltip=None):
        self.hicon = hicon
        self.tooltip = tooltip
        
    def show(self):
        """Display the taskbar icon"""
        flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE
        if self.tooltip is not None:
            flags |= win32gui.NIF_TIP
            nid = (self.hwnd, 0, flags, win32con.WM_USER+20, self.hicon, self.tooltip)
        else:
            nid = (self.hwnd, 0, flags, win32con.WM_USER+20, self.hicon)
        if self.visible:
            self.hide()
        win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)
        self.visible = 1

    def hide(self):
        """Hide the taskbar icon"""
        if self.visible:
            nid = (self.hwnd, 0)
            win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)
        self.visible = 0
        
    def onDestroy(self, hwnd, msg, wparam, lparam):
        self.hide()
        win32gui.PostQuitMessage(0) # Terminate the app.



    def onCommand(self, hwnd, msg, wparam, lparam):
        id = win32gui.LOWORD(wparam)
        if id == 1024:
            self.parent.activate_menu()
        elif id == 1025:
            self.parent.on_preferences_clicked(None)
        elif id == 1026:
            self.hide()
            self.parent.on_logout_clicked(None)
        elif id == 1027:
            self.hide()
            self.parent.close_pms() 
    
    def onTaskbarNotify(self, hwnd, msg, wparam, lparam):
        if lparam == win32con.WM_LBUTTONDBLCLK:
            self.onDoubleClick()
        elif lparam ==  win32con.WM_RBUTTONUP:
            self.onRightClick()
        
        return 1

    def onClick(self):
        """Override in subclassess"""
        pass

    def onDoubleClick(self):
        """Override in subclassess"""
        pass
    
    def onRightClick(self):
        """Override in subclasses"""
        pass


class DemoTaskbar(Taskbar):

    def __init__(self, parent):
        Taskbar.__init__(self)
        print 'hello hello'
        self.parent = parent
        hinst = win32gui.GetModuleHandle(None)
        print 'i can say'
        flags = win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE
        print 'hello'
        try:
            icon = win32gui.LoadImage(hinst, "default.ico",
                                      win32con.IMAGE_ICON, 0, 0, flags)
        except:
            icon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)
        print 'made it'
        self.setIcon(icon)
        print ' one more dune to go'
        self.show()
        print 'fuck!'
        
    def onClick(self):
        self.parent.activate_menu()
        
    def onRightClick(self):
        menu = win32gui.CreatePopupMenu()
        win32gui.AppendMenu( menu, win32con.MF_STRING, 1024, "Open")
        win32gui.AppendMenu( menu, win32con.MF_STRING, 1025, "Preferences")
        win32gui.AppendMenu( menu, win32con.MFT_SEPARATOR, 1029, "")
        win32gui.AppendMenu( menu, win32con.MF_STRING, 1026, "Logout")
        win32gui.AppendMenu(menu, win32con.MF_STRING, 1027, "Quit")
        pos = win32gui.GetCursorPos()
        win32gui.SetForegroundWindow(self.hwnd)
        win32gui.TrackPopupMenu(menu, win32con.TPM_LEFTALIGN, pos[0], pos[1],  
0, self.hwnd, None)
        win32gui.PostMessage(self.hwnd, win32con.WM_NULL, 0, 0)
        return 1

    def onDoubleClick(self):
        print "you double clicked, bye!"
        win32gui.PostQuitMessage(0)

    def new_message(self, title, message, timeout=5):
        #NIF_INFO flag below enables balloony stuff
        flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_INFO
        nid = (self.hwnd, 0, flags, win32con.WM_USER+20,
               self.hicon, "", message,
               timeout, title, win32gui.NIF_MESSAGE)
        #change our already present icon ...
        win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY, nid)
        win32gui.PumpWaitingMessages()
        

if __name__ == "__main__":
    t = DemoTaskbar()
    win32gui.PumpMessages() # start demo
