using System;
using System.Collections.Generic;
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
        private const int _previousDayMenuItemTag = 101;
        private const int _nextDayMenuItemTag = 102;
        private const int _previousScreenMenuItemTag = 103;
        private const int _nextScreenMenuItemTag = 104;
        private const int _previousScreeningMenuItemTag = 105;
        private const int _nextScreeningMenuItemTag = 106;
        private const int _FirstFestivalDaysMenuItemTag = 110;
        private readonly ViewController _controller;
        private List<NSMenuItem> _dayItems;
        #endregion

        #region Constructors
        public NavigateMenuDelegate(ViewController controller)
        {
            _controller = controller;
            _dayItems = new List<NSMenuItem> { };
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
        private void PopulateFestivalDaysMenu(NSMenu menu)
        {
            // Delete existing festival day menu items.
            foreach (var menuItem in _dayItems)
            {
                menu.RemoveItem(menuItem);
            }

            // Loop through the festival days
            _dayItems = new List<NSMenuItem> { };
            var plan = _controller.Plan;
            var tag = _FirstFestivalDaysMenuItemTag;
            foreach (var day in ScreeningsPlan.FestivalDays)
            {
                var item = new NSMenuItem(ItemTitle(day));
                item.Tag = tag++;
                item.Enabled = day != plan.CurrDay;
                item.Activated += (sender, e) => _controller.GoToDay(day);
                menu.AddItem(item);
                _dayItems.Add(item);
            }
        }

        private string ItemTitle(DateTime day)
        {
            return Screening.LongDayString(day);
        }
        #endregion
    }
}
