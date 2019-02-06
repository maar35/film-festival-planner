using System;
using Foundation;
using AppKit;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Titled button, button that uses the ITitled interface to set its title.
    /// </summary>

    [Register ("TitledButton")]
    public class TitledButton : NSButton, ITitled
    {
        #region Constructors
        public TitledButton(IntPtr handle) : base(handle)
        {
        }
		#endregion

        #region Public Methods
        public void SetTitle(string title)
        {
            base.Title = title;
        }
        #endregion
    }
}
