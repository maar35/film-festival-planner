using System;
using AppKit;
using PresentScreenings.TableView.Utilities;

namespace PresentScreenings.TableView
{
    public class CombinationWindowDelegate : BaseWindowDelegate
    {
        #region Private Members
        private static StringByBoolBool _subjectByRatingScreeningInfoChanged;
        #endregion

        #region Properties
        public static bool ScreeningInfoChanged { get; set; }
        #endregion

        #region Constructors
        static CombinationWindowDelegate()
        {
            _subjectByRatingScreeningInfoChanged = new StringByBoolBool();
            _subjectByRatingScreeningInfoChanged.Set(true, true, "ratings and screening info");
            _subjectByRatingScreeningInfoChanged.Set(true, false, "film ratings");
            _subjectByRatingScreeningInfoChanged.Set(false, true, "screening info");
            ScreeningInfoChanged = false;
        }

        public CombinationWindowDelegate(NSWindow window, Action saveAction) : base(window, saveAction)
        {
            Window = window;
            SaveAction = saveAction;
        }
        #endregion

        #region Override Methods
        public override bool WindowShouldClose(Foundation.NSObject sender)
        {
            // is the window dirty?
            if (Window.DocumentEdited)
            {
                // Check if the static indicators have been cleared in the
                // application termation process without clearing the non-static
                // Document Edited flags.
                if (!ScreeningInfoChanged)
                {
                    return true;
                }

                // Set the text in the save dialog depending on what changed.
                Subject = "screening info";

                // Save the changed data.
                return base.WindowShouldClose(sender);
            }
            return true;
        }
        #endregion

        #region Public Mathods
        public static void SaveChangedData()
        {
            // Save the screening info when changed.
            if (ScreeningInfoChanged)
            {
                ScreeningDialogController.SaveScreeningInfo();
            }
        }
        #endregion
    }
}
