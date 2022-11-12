using System;
using System.Linq;
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
        private const float _labelTop = ControlsFactory.VerticalPixelsBetweenLabels;
        private const float _yLine = ControlsFactory.StandardLineHeight;
        private const int _linesPerScreening = 2;
        private const float _labelHeight = _yLine * _linesPerScreening;
        #endregion

        #region Private Variables
        private nfloat _labelLeft;
        private nfloat _labelWidth;
        private ViewController _controller;
        private ScreeningsTableView _superView;
        #endregion

        #region Properties
        public static float HorizontalScreeningsViewMargin => _labelHeight;
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
            var elegableScreenings = plan.ScreenScreenings[day][screen];
            foreach (var screening in elegableScreenings)
            {
                _controller.UpdateWarning(screening);
                _labelLeft = _superView.NumberOfPixelsFromTime(screening.StartTime);
				_labelWidth = _superView.NumberOfPixelsFromDuration(screening.Duration);
                CGRect rect = new CGRect(_labelLeft, _labelTop, _labelWidth, _labelHeight);
                var screeningControl = new DaySchemaScreeningControl(rect, screening);
                screeningControl.Selected = screening == currScreening;
                screeningControl.ScreeningSelected += (s, e) => SegueToScreeningWindow((DaySchemaScreeningControl)s);
                view.AddSubview(screeningControl);
                _controller.AddScreeningControl(screening, screeningControl);
			}
		}

        public void SegueToScreeningWindow(DaySchemaScreeningControl sender)
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
