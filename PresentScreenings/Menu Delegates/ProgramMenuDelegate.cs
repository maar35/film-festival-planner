using System;
using AppKit;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Program menu delegate, enables and disables the items of the program
    /// menu, based on their tag value.
    /// </summary>

    public class ProgramMenuDelegate : NSMenuDelegate
    {
        #region Private Members
        const int _plannerMenuItemTag = 601;
        const int _analyserMenuItemTag = 602;
        const int _availabilityMenuItemTag = 603;
        private readonly AppDelegate _app;
        private readonly ViewController _controller;
        #endregion

        #region Constructors
        public ProgramMenuDelegate(AppDelegate app, NSMenu menu)
        {
            _app = app;
            _controller = app.Controller;
        }
        #endregion

        #region Override Methods
        public override void MenuWillHighlightItem(NSMenu menu, NSMenuItem item)
        {
        }

        public override void NeedsUpdate(NSMenu menu)
        {
            // Process every item in the menu
            foreach (NSMenuItem item in menu.Items)
            {
                // If the main view is inactive, all menu items must be inactive.
                if (!_controller.ViewIsActive())
                {
                    item.Enabled = false;
                    continue;
                }

                // Take action based on the menu tag.
                switch (item.Tag)
                {
                    case _plannerMenuItemTag:
                        item.Enabled = true;
                        break;
                    case _analyserMenuItemTag:
                        item.Enabled = true;
                        break;
                    case _availabilityMenuItemTag:
                        item.Enabled = true;
                        break;
                    default:
                        item.Enabled = false;
                        break;
                }
            }
        }
        #endregion
    }
}
