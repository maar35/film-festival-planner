using System;
using AppKit;

namespace PresentScreenings.TableView
{
    public class RatingField : NSTextField
    {
        #region Properties
        public FilmRatingDialogController DialogController { get; }
        private NSCell CocoaCloseButton => (NSCell)DialogController.View.Window.AccessibilityCloseButton;
        #endregion

        #region Constructors
        public RatingField(FilmRatingDialogController dialogController)
        {
            DialogController = dialogController;
        }
        #endregion

        #region Override Methods
        public override bool ShouldBeginEditing(NSText textObject)
        {
            bool began = base.ShouldBeginEditing(textObject);
            if (began)
            {
                DialogController.TextBeingEdited = true;
                CocoaCloseButton.Enabled = false;
            }
            return began;
        }

        public override bool ShouldEndEditing(NSText textObject)
        {
            bool ended = base.ShouldEndEditing(textObject);
            if (ended)
            {
                DialogController.TextBeingEdited = false;
                CocoaCloseButton.Enabled = true;
            }
            return ended;
        }

        public override bool AbortEditing()
        {
            bool aborted = base.AbortEditing();
            if (aborted)
            {
                DialogController.TextBeingEdited = false;
                CocoaCloseButton.Enabled = true;
            }
            return aborted;
        }
        #endregion
    }
}
