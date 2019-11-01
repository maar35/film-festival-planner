using System;
using AppKit;
using CoreGraphics;
using CoreText;
using Foundation;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Screening control, when clicked opens a dialog to view and edit editable
    /// screening data.
    /// The control displays a summary of its screening. The display area is
    /// only clickable in Use Core Graphics mode.
    /// </summary>

    [Register("NSScreeningControl")]
    public class ScreeningControl : NSControl
    {
        #region Private Variables
        static nfloat _xExtension;
        bool _selected = false;
        CGRect _screeningRect;
        Screening _screening;
        ScreeningLabel _label;
        ScreeningButton _button;
        #endregion

        #region Application Access
        private static AppDelegate _app => (AppDelegate)NSApplication.SharedApplication.Delegate;
        #endregion

        #region Properties
        public static bool UseCoreGraphics { get; set; }
        public Screening Screening => _screening;
        public bool Selected
        {
            get => _selected;
            set
            {
                _selected = value;
                if (value)
                {
                    // Make the view scroll as to make the control visible.
                    var plan = _app.Controller.Plan;
                    var table = _app.Controller.TableView;
                    _app.Controller.TableView.ScrollRowToVisible(plan.CurrDayScreens.IndexOf(plan.CurrScreen));
                    var x = Frame.X;
                    var y = Frame.Y + plan.CurrDayScreens.IndexOf(plan.CurrScreen) *(table.RowHeight + table.IntercellSpacing.Height);
                    var frame = new CGRect(x, y, Frame.Width, Frame.Height);
                    _app.Controller.TableView.ScrollRectToVisible(frame);
                }

                // Force a redraw.
                NeedsDisplay = true;
            }
        }
        #endregion

        #region Constructors
        public ScreeningControl(CGRect screeningRect, Screening screening) : base(ControlRect(screeningRect))
        {
            Initialize();
            _screening = screening;
            _screeningRect = screeningRect;
            nfloat clickWidth = _screeningRect.Height;
            nfloat clickHeigt = _screeningRect.Height;
            CGRect labelRect = new CGRect(_xExtension, 0, Frame.Width - _xExtension, Frame.Height);
            if (UseCoreGraphics)
            {
                _button = new ScreeningButton(labelRect, _screening);
                _button.Activated += (sender, e) => ShowScreeningInfo(_screening);
				base.AddSubview(_button);
            }
            else
            {
                _label = new ScreeningLabel(labelRect, _screening);
				base.AddSubview(_label);
            }
            StringValue = _screening.ToScreeningLabelString();
            Alignment = NSTextAlignment.Left;
            LineBreakMode = NSLineBreakMode.TruncatingMiddle;
            Font = NSFont.BoldSystemFontOfSize(13);
        }

        void Initialize()
        {
            WantsLayer = true;
            LayerContentsRedrawPolicy = NSViewLayerContentsRedrawPolicy.OnSetNeedsDisplay;
        }
        #endregion

        #region Override Methods
        public override void DrawRect(CGRect dirtyRect)
        {
            base.DrawRect(dirtyRect);

            // Use Core Graphic routines to draw our UI
            var side = Frame.Height;
            using (CGContext g = NSGraphicsContext.CurrentContext.GraphicsPort)
            {
                // Define the clickable rect
                var clickableRect = new CGRect(0, 0, _xExtension - 2, side);

                // Draw the clickable rect
                DrawClickRect(g, clickableRect);

                // Draw a frame if something's wrong with tickets
                if (ScreeningInfo.TicketStatusNeedsAttention(_screening))
                {
                    ColorView.DrawTicketAvalabilityFrame(g, _screening, side);
                }

                // Draw Sold Out Symbol
                if(_screening.SoldOut)
                {
                    ColorView.DrawSoldOutSymbol(g, Selected, clickableRect);
                }

                // Draw a warningsymbol
                if (_screening.Warning != ScreeningInfo.Warning.NoWarning)
                {
                    DrawWarningMiniature(g, side);
                }

                // Draw the rating of the film
                var film = ViewController.GetFilmById(_screening.FilmId);
                var rating = ViewController.GetMaxRating(film);
                if (rating.IsGreaterOrEqual(FilmRating.LowestSuperRating) || rating.Equals(FilmRating.Unrated))
                {
                    DrawRating(g, side, rating, _screening.IAttend);
                }
            }
        }
        #endregion

        #region Mouse Handling Methods
        // --------------------------------------------------------------------------------
        // Handle mouse with Override Methods.
        // NOTE: Use either this method or Gesture Recognizers, NOT both!
        // --------------------------------------------------------------------------------
        public override void MouseDown(NSEvent theEvent)
        {
            base.MouseDown(theEvent);
            RaiseScreeningSelected();
        }

        public override void MouseDragged(NSEvent theEvent)
        {
            base.MouseDragged(theEvent);
        }

        public override void MouseUp(NSEvent theEvent)
        {
            base.MouseUp(theEvent);
        }

        public override void MouseMoved(NSEvent theEvent)
        {
            base.MouseMoved(theEvent);
        }
        #endregion

        #region Events
        public event EventHandler ScreeningSelected;

        internal void RaiseScreeningSelected()
        {
            ScreeningSelected?.Invoke(this, EventArgs.Empty);
        }

        public event EventHandler ValueChanged;

        internal void RaiseValueChanged()
        {
            ValueChanged?.Invoke(this, EventArgs.Empty);

            // Perform any action bound to the control from Interface Builder
            // via an Action.
            if (Action != null)
            {
                NSApplication.SharedApplication.SendAction(Action, Target, this);
            }
        }
        #endregion

        #region Private Methods
        void FlipSwitchState()
        {
            RaiseValueChanged();
        }

        void DrawClickRect(CGContext g, CGRect clickRect)
        {
            var gpath = new CGPath();
            gpath.AddRect(clickRect);
            ColorView.ClickPadBackgroundColor(Selected).SetFill();
            gpath.CloseSubpath();
            g.AddPath(gpath);
            g.DrawPath(CGPathDrawingMode.Fill);
        }

        void DrawWarningMiniature(CGContext g, nfloat side)
        {
            nfloat shift = side*6/16;
            g.SetLineWidth(1);
            NSColor.Black.SetStroke();
            NSColor.Yellow.SetFill();
            var trianglePath = new CGPath();
            trianglePath.AddLines(new CGPoint[]{
                new CGPoint(shift + side*1/16, side*1/16),
                new CGPoint(shift + side*4/16, side*7/16),
                new CGPoint(shift + side*7/16, side*1/16)
            });
            trianglePath.CloseSubpath();
            g.AddPath(trianglePath);
            g.DrawPath(CGPathDrawingMode.FillStroke);
            var barPath = new CGPath();
            barPath.AddLines(new CGPoint[]{
                new CGPoint(shift + side*4/16, side*2/16),
                new CGPoint(shift + side*4/16, side*5/16)
            });
            barPath.CloseSubpath();
            g.AddPath(barPath);
            g.DrawPath(CGPathDrawingMode.Stroke);
        }

        void DrawRating(CGContext g, nfloat side, FilmRating rating, bool withPi = false)
        {
            NSColor textColor = ColorView.ClickPadTextColor(Selected);
            float fontSize = 13.0f;
            g.TranslateCTM(0, fontSize);
            g.SetTextDrawingMode(CGTextDrawingMode.Fill);
            g.SetFillColor(textColor.CGColor);
            g.TextPosition = new CGPoint(side/2 - 2, 7);
            string ratingText = rating.ToString();
            if (withPi)
            {
                ratingText += "𝜋";
            }
            var attributedString = new NSAttributedString(
                ratingText,
                new CTStringAttributes
                {
                    ForegroundColorFromContext = true,
                    Font = new CTFont("Helvetica-Bold", fontSize)
                });
            using (var textLine = new CTLine(attributedString))
            {
                textLine.Draw(g);
            }
        }

        static CGRect ControlRect(CGRect screeningRect)
        {
            _xExtension = screeningRect.Height;
            nfloat x = screeningRect.X;
            nfloat y = screeningRect.Y;
            nfloat w = screeningRect.Width;
            nfloat h = screeningRect.Height;
            return new CGRect(x - _xExtension, y, w + _xExtension, h);
        }

        void ShowScreeningInfo(Screening screening)
        {
            ViewController controller = ((AppDelegate)NSApplication.SharedApplication.Delegate).Controller;
            controller.GoToScreening((screening));
        }
        #endregion
    }
}
