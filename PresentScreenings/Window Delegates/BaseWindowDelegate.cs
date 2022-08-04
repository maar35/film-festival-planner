using System;
using AppKit;

namespace PresentScreenings.TableView
{
    public class BaseWindowDelegate : NSWindowDelegate
    {
        #region Properties
        protected NSWindow Window { get; set; }
        protected Action SaveAction { get; set; }
        protected string Subject { get; set; }
        #endregion

        #region Constructors
        public BaseWindowDelegate(NSWindow window, Action saveAction, string subject=null)
        {
            Window = window;
            SaveAction = saveAction;
            Subject = subject == null ? "data" : subject;
        }
        #endregion

        #region Override Methods
        public override bool WindowShouldClose(Foundation.NSObject sender)
        {
            // is the window dirty?
            if (Window.DocumentEdited)
            {
                string messageText = "Save Changed Data";
                string informativeText = $"Save {Subject} before closing window?";
                return AlertRaiser.RunDirtyWindowAlert(messageText, informativeText, SaveAction);
            }
            return true;
        }
        #endregion
    }
}
