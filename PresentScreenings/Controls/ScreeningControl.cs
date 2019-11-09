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
        private static nfloat _xExtension;
        private bool _selected = false;
        private CTStringAttributes _stringAttributes;
        private CGRect _screeningRect;
        private ScreeningLabel _label;
        private ScreeningButton _button;
        #endregion

        #region Application Access
        private static AppDelegate _app => (AppDelegate)NSApplication.SharedApplication.Delegate;
        #endregion

        #region Properties
        public static bool UseCoreGraphics { get; set; }
        public static nfloat FontSize { get; } = 13;
        public static CTFont StandardFont { get; } = new CTFont(".AppleSystemUIFontBold", FontSize);
        public Screening Screening { get; }
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
            Screening = screening;
            _screeningRect = screeningRect;
            nfloat clickWidth = _screeningRect.Height;
            nfloat clickHeigt = _screeningRect.Height;
            CGRect labelRect = new CGRect(_xExtension, 0, Frame.Width - _xExtension, Frame.Height);
            if (UseCoreGraphics)
            {
                _button = new ScreeningButton(labelRect, Screening);
                _button.Activated += (sender, e) => ShowScreeningInfo(Screening);
				base.AddSubview(_button);
            }
            else
            {
                _label = new ScreeningLabel(labelRect, Screening);
				base.AddSubview(_label);
            }
            StringValue = Screening.ToScreeningLabelString();
            Alignment = NSTextAlignment.Left;
            LineBreakMode = NSLineBreakMode.TruncatingMiddle;
            Font = NSFont.BoldSystemFontOfSize(FontSize);
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

            // Use Core Graphics routines to draw our UI.
            var side = Frame.Height;
            using (CGContext context = NSGraphicsContext.CurrentContext.GraphicsPort)
            {
                // Define the clickable rect.
                var clickableRect = new CGRect(0, 0, _xExtension - 2, side);

                // Draw the clickable rect.
                DrawClickRect(context, clickableRect);

                // Draw a frame if something's wrong with tickets.
                if (ScreeningInfo.TicketStatusNeedsAttention(Screening))
                {
                    ColorView.DrawTicketAvalabilityFrame(context, Screening, side);
                }

                // Draw Sold Out symbol.
                if(Screening.SoldOut)
                {
                    ColorView.DrawSoldOutSymbol(context, Selected, clickableRect);
                }

                // Draw a warning symbol.
                if (Screening.Warning != ScreeningInfo.Warning.NoWarning)
                {
                    DrawWarningMiniature(context, side);
                }

                // Initialize CoreText settings.
                InitializeCoreText(context);

                // Draw Automatically Planned symbol.
                if (Screening.AutomaticallyPlanned)
                {
                    DrawAutomaticallyPlannedSymbol(context, side);
                }

                // Draw the rating of the film
                var film = ViewController.GetFilmById(Screening.FilmId);
                var rating = ViewController.GetMaxRating(film);
                if (rating.IsGreaterOrEqual(FilmRating.LowestSuperRating) || rating.Equals(FilmRating.Unrated))
                {
                    DrawRating(context, side, rating);
                }
            }
        }
        #endregion

        #region Private Methods
        private void FlipSwitchState()
        {
            RaiseValueChanged();
        }

        private void DrawClickRect(CGContext context, CGRect clickRect)
        {
            var gpath = new CGPath();
            gpath.AddRect(clickRect);
            ColorView.ClickPadBackgroundColor(Selected).SetFill();
            gpath.CloseSubpath();
            context.AddPath(gpath);
            context.DrawPath(CGPathDrawingMode.Fill);
        }

        private void DrawWarningMiniature(CGContext context, nfloat side)
        {
            nfloat x = side*1/16;
            nfloat y = side*4/16;
            context.SetLineWidth(1);
            NSColor.Black.SetStroke();
            NSColor.Yellow.SetFill();
            var trianglePath = new CGPath();
            trianglePath.AddLines(new CGPoint[]{
                new CGPoint(x + side*1/16, y + side*1/16),
                new CGPoint(x + side*4/16, y + side*7/16),
                new CGPoint(x + side*7/16, y + side*1/16)
            });
            trianglePath.CloseSubpath();
            context.AddPath(trianglePath);
            context.DrawPath(CGPathDrawingMode.FillStroke);
            var barPath = new CGPath();
            barPath.AddLines(new CGPoint[]{
                new CGPoint(x + side*4/16, y + side*2/16),
                new CGPoint(x + side*4/16, y + side*5/16)
            });
            barPath.CloseSubpath();
            context.AddPath(barPath);
            context.DrawPath(CGPathDrawingMode.Stroke);
        }

        private void InitializeCoreText(CGContext context)
        {
            context.TranslateCTM(-1 , ScreeningsView.VerticalTextOffset);
            NSColor textColor = ColorView.ClickPadTextColor(Selected);
            context.SetTextDrawingMode(CGTextDrawingMode.Fill);
            context.SetFillColor(textColor.CGColor);
            _stringAttributes = new CTStringAttributes
            {
                ForegroundColorFromContext = true,
                Font = StandardFont
            };
        }

        private void DrawRating(CGContext context, nfloat side, FilmRating rating)
        {
            DrawText(context, rating.ToString(), side/2, ScreeningsView.ScreeningControlLineHeight);
        }

        private void DrawAutomaticallyPlannedSymbol(CGContext context, nfloat side)
        {
            DrawText(context, "𝛑", side/2, 0); // MATHEMATICAL BOLD SMALL PI = 𝛑
        }

        private void DrawText(CGContext context, string text, nfloat x, nfloat y)
        {
            context.TextPosition = new CGPoint(x, y);
            var attributedString = new NSAttributedString(text, _stringAttributes);
            using (var textLine = new CTLine(attributedString))
            {
                textLine.Draw(context);
            }
        }

        private static CGRect ControlRect(CGRect screeningRect)
        {
            _xExtension = screeningRect.Height;
            nfloat x = screeningRect.X;
            nfloat y = screeningRect.Y;
            nfloat w = screeningRect.Width;
            nfloat h = screeningRect.Height;
            return new CGRect(x - _xExtension, y, w + _xExtension, h);
        }

        private void ShowScreeningInfo(Screening screening)
        {
            _app.Controller.GoToScreening(screening);
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
    }
}
