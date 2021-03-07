using System;
namespace PresentScreenings.TableView
{
    public class OnLineScreening : Screening
    {
        #region Private Variables
        protected Screen _displayScreen;
        #endregion

        #region Constructors
        public OnLineScreening(string screeningText) : base(screeningText)
        {
            DisplayScreen = Screen;
        }
        #endregion

        #region Override Methods
        protected override Screen GetDisplayScreen()
        {
            return _displayScreen;
        }

        protected override void SetDisplayScreen(Screen screen)
        {
            _displayScreen = screen;
        }
        #endregion
    }
}
