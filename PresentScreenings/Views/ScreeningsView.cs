using System;
using AppKit;
using CoreGraphics;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Screenings view, responsible to draw the screenings of a given theater
    /// screen and manage the corresponding controls.
    /// </summary>

    public class ScreeningsView
	{
        #region Private Constants
        const float _labelTop = 2;
        const float _yLine = 17;
        const int _linesPerScreening = 2;
        const float _labelHeight = _yLine * _linesPerScreening;
        #endregion

        #region Public Constants
        public const float HorizontalScreeningControlExtensionPixels = _labelHeight;
        public const float ScreeningControlLineHeight = _yLine;
        public const float VerticalTextOffset = 3;
        #endregion

        #region Private Variables
        nfloat _labelLeft;
        nfloat _labelWidth;
        ViewController _controller;
        ScreeningsTableView _superView;
        #endregion

        #region Constructors
        public ScreeningsView(ViewController controller, ScreeningsTableView superView)
		{
			_controller = controller;
            _superView = superView;
		}
        #endregion

        #region Public methods
        public void DrawScreenings(NSClipView view, ScreeningsPlan plan, DateTime day, Screen screen)
		{
			DisposeSubViews(view);
            var currScreening = plan.CurrScreening;
            foreach (var screening in plan.ScreenScreenings[day][screen])
            {
                _controller.UpdateWarning(screening);
                _labelLeft = _superView.NumberOfPixelsFromTime(screening.StartTime);
				_labelWidth = _superView.NumberOfPixelsFromDuration(screening.Duration);
                CGRect rect = new CGRect(_labelLeft, _labelTop, _labelWidth, _labelHeight);
                var screeningControl = new ScreeningControl(rect, screening);
                screeningControl.Selected = screening == currScreening;
                screeningControl.ScreeningSelected += (s, e) => SegueToScreeningWindow((ScreeningControl)s);
                view.AddSubview(screeningControl);
                _controller.AddScreeningControl(screening, screeningControl);
			}
		}

        public void SegueToScreeningWindow(ScreeningControl sender)
        {
            _controller.GoToScreening(sender.Screening);
        }

        public static void DisposeSubViews(NSView view)
		{
			foreach (var subView in view.Subviews)
			{
				subView.RemoveFromSuperview();
				subView.Dispose();
			}
		}
		#endregion
	}
}
