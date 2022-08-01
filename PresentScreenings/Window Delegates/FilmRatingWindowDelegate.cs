using System;
using System.Collections.Generic;
using AppKit;

namespace PresentScreenings.TableView
{
    public class FilmRatingWindowDelegate : NSWindowDelegate
    {
        #region Private Members
        private Dictionary<Tuple<bool, bool>, string> _subjectByRatingScreeningInfoChanged;
        #endregion
        #region Computed Properties
        public NSWindow Window { get; set; }
        #endregion

        #region Constructors
        public FilmRatingWindowDelegate(NSWindow window)
        {
            Window = window;
            _subjectByRatingScreeningInfoChanged = new Dictionary<Tuple<bool, bool>, string> { };
            _subjectByRatingScreeningInfoChanged[new Tuple<bool, bool>(true, true)] = "ratings and screening info";
            _subjectByRatingScreeningInfoChanged[new Tuple<bool, bool>(true, false)] = "film ratings";
            _subjectByRatingScreeningInfoChanged[new Tuple<bool, bool>(false, true)] = "screening info";
        }
        #endregion

        #region Override Methods
        public override bool WindowShouldClose(Foundation.NSObject sender)
        {
            // is the window dirty?
            if (Window.DocumentEdited)
            {

                string messageText = "Save Changed Data";
                string subject = _subjectByRatingScreeningInfoChanged[
                    new Tuple<bool, bool>(
                        FilmRating.RatingChanged,
                        FilmRatingDialogController.ScreeningInfoChangedInRatingDialog
                    )];
                string informativeText = $"Save {subject} before closing window?";
                return AlertRaiser.RunDirtyWindowAlert(messageText, informativeText, this, SaveAction);
            }
            return true;
        }
        #endregion

        #region Private methods
        private void SaveAction(NSWindowDelegate windowDelegate)
        {
            var window = (windowDelegate as FilmRatingWindowDelegate).Window;
            var viewController = window.ContentViewController as FilmRatingDialogController;
            viewController.CloseDialog();
        }
        #endregion
    }
}
