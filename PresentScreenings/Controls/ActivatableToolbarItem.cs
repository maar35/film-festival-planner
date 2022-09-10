using System;
using AppKit;
using Foundation;

namespace PresentScreenings.TableView
{
    [Register("ActivatableToolbarItem")]
    public class ActivatableToolbarItem : NSToolbarItem
    {
        public bool Active { get; set; } = true;

        public ActivatableToolbarItem()
        {
        }

        public ActivatableToolbarItem(IntPtr handle) : base (handle)
        {
        }

        public ActivatableToolbarItem(NSObjectFlag t) : base (t)
        {
        }

        public override void Validate()
        {
            base.Validate();
            Enabled = Active;
        }
    }
}
