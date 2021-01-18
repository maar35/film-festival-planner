using System;
using AppKit;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Navigate menu delegate, enables and disables the items of the navigation
    /// menu, based on their tag value and methods of the given View Controller.
    /// </summary>

    public class NavigateMenuDelegate : NSMenuDelegate
    {
        #region Private Members
        static nint _ItemCountStart = 100;
        const int _previousDayMenuItemTag = 101;
        const int _nextDayMenuItemTag = 102;
        const int _previousScreenMenuItemTag = 103;
        const int _nextScreenMenuItemTag = 104;
        const int _previousScreeningMenuItemTag = 105;
        const int _nextScreeningMenuItemTag = 106;
        bool _festivalDaysMenuItemsInitialized = false;
        ViewController _controller;
        #endregion

        #region Constructors
        public NavigateMenuDelegate(NSMenu menu, ViewController controller)
        {
            _controller = controller;
        }
        #endregion

        #region Override Methods
        public override void MenuWillHighlightItem(NSMenu menu, NSMenuItem item)
        {
        }

        public override void NeedsUpdate(NSMenu menu)
        {
            // Build up the Festival Days Menu Items.
            PopulateFestivalDaysMenu(menu);

            // Process every item in the menu
            foreach (NSMenuItem item in menu.Items)
            {
                // If the main view is inactive, all menu items must be inactive.
                if (! _controller.ViewIsActive())
                {
                    item.Enabled = false;
                    continue;
                }

                // Take action based on the menu tag.
                switch (item.Tag)
                {
                    case _previousDayMenuItemTag:
                        item.Enabled = _controller.Plan.NextDayExists(-1);
                        break;
                    case _nextDayMenuItemTag:
                        item.Enabled = _controller.Plan.NextDayExists(1);
                        break;
                    case _previousScreenMenuItemTag:
                        item.Enabled = _controller.Plan.NextScreenWithinDayExists(-1);
                        break;
                    case _nextScreenMenuItemTag:
                        item.Enabled = _controller.Plan.NextScreenWithinDayExists(1);
                        break;
                    case _previousScreeningMenuItemTag:
                        item.Enabled = _controller.Plan.PrevScreeningWithinDayExists();
                        break;
                    case _nextScreeningMenuItemTag:
                        item.Enabled = _controller.Plan.NextScreeningWithinDayExists();
                        break;
                    default:
                        item.Enabled = item.Title != ItemTitle(_controller.Plan.CurrDay);
                        break;
                }
            }
        }
        #endregion

        #region Private Members
        void PopulateFestivalDaysMenu(NSMenu menu)
        {
            // Check if the menu items need to be initialized.
            if(_festivalDaysMenuItemsInitialized)
            {
                return;
            }

            // Loop through the festival days
            var plan = _controller.Plan;
            foreach (var day in ScreeningsPlan.FestivalDays)
            {
                NSMenuItem item = new NSMenuItem(ItemTitle(day));
                item.Tag = _ItemCountStart + menu.Count;
				item.Enabled = day != plan.CurrDay;
                item.Activated += (sender, e) => _controller.GoToDay(day);
                menu.AddItem(item);
            }
            _festivalDaysMenuItemsInitialized = true;
        }

        string ItemTitle(DateTime day)
        {
            return Screening.LongDayString(day);
        }
        #endregion
    }
}
