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

    public class DaySchemaScreeningControl : PointingHandControl
    {
        #region Private Variables
        private static nfloat _xExtension;
        private bool _selected = false;
        private static CTStringAttributes _stringAttributes;
        #endregion

        #region Application Access
        private static AppDelegate _app => (AppDelegate)NSApplication.SharedApplication.Delegate;
        #endregion

        #region Properties
        public static bool UseCoreGraphics { get; set; }
        public static string AutomaticallyPlannedSymbol { get; } = "𝛑"; // MATHEMATICAL BOLD SMALL PI = 𝛑
        public Screening Screening { get; }
        public CGRect ClickPadRect { get; }
        public CGRect LabelRect { get; }
        public bool Selected { get => _selected; set => SetSelected(value); }
        #endregion

        #region Constructors
        public DaySchemaScreeningControl(CGRect screeningRect, Screening screening) : base(GetExtendedRect(screeningRect))
        {
            // Initialize control features.
            WantsLayer = true;
            LayerContentsRedrawPolicy = NSViewLayerContentsRedrawPolicy.OnSetNeedsDisplay;

            // Initialize properties.
            Screening = screening;
            ClickPadRect = new CGRect(0, 0, _xExtension - 2, Frame.Height);
            LabelRect = new CGRect(_xExtension, 0, Frame.Width - _xExtension, Frame.Height);

            // Add a control depending whether core graphics are used to draw
            // the label. If core graphics are used, the label is clickable.
            if (UseCoreGraphics)
            {
                var control = new ClickableScreeningLabel(LabelRect, Screening);
                control.Activated += (sender, e) => ShowScreeningInfo(Screening);
				base.AddSubview(control);
            }
            else
            {
                var label = new ScreeningLabel(LabelRect, Screening);
				base.AddSubview(label);
            }
        }
        #endregion

        #region Override Methods
        public override void MouseDown(NSEvent theEvent)
        {
            base.MouseDown(theEvent);
            RaiseScreeningSelected();
        }

        public override void DrawRect(CGRect dirtyRect)
        {
            base.DrawRect(dirtyRect);

            // Use Core Graphics routines to draw our UI.
            var side = Frame.Height;
            using (CGContext context = NSGraphicsContext.CurrentContext.GraphicsPort)
            {
                // Define the clickable rect.
                var clickableRect = ClickPadRect;

                // Draw the clickable rect.
                DrawClickRect(context, clickableRect);

                // Draw a frame if something's wrong with tickets.
                if (ScreeningInfo.TicketStatusNeedsAttention(Screening))
                {
                    ColorView.DrawTicketAvalabilityFrame(context, Screening, side);
                }

                // Draw a progress bar if the screening is on-demand.
                if (Screening is OnDemandScreening onDemandScreening)
                {
                    ColorView.DrawOnDemandAvailabilityStatus(context, onDemandScreening, side, Selected);
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
                InitializeCoreText(context, Selected);

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

        #region Public Methods
        public static void InitializeCoreText(CGContext context, bool selected)
        {
            context.TranslateCTM(-1, ScreeningsView.VerticalTextOffset);
            NSColor textColor = ColorView.ClickPadTextColor(selected);
            context.SetTextDrawingMode(CGTextDrawingMode.Fill);
            context.SetFillColor(textColor.CGColor);
            _stringAttributes = new CTStringAttributes
            {
                ForegroundColorFromContext = true,
                Font = ControlsFactory.StandardCtBondFont,
            };
        }

        public static void DrawText(CGContext context, string text, nfloat x, nfloat y)
        {
            context.TextPosition = new CGPoint(x, y);
            var attributedString = new NSAttributedString(text, _stringAttributes);
            using (var textLine = new CTLine(attributedString))
            {
                textLine.Draw(context);
            }
        }
        #endregion

        #region Private Methods
        private void SetSelected(bool selected)
        {
            _selected = selected;
            if (selected)
            {
                // Scroll the view as to make the control visible.
                var plan = _app.Controller.Plan;
                var table = _app.Controller.TableView;
                _app.Controller.TableView.ScrollRowToVisible(plan.CurrDayScreens.IndexOf(plan.CurrScreen));
                var x = Frame.X;
                var y = Frame.Y + plan.CurrDayScreens.IndexOf(plan.CurrScreen) * (table.RowHeight + table.IntercellSpacing.Height);
                var frame = new CGRect(x, y, Frame.Width, Frame.Height);
                _app.Controller.TableView.ScrollRectToVisible(frame);
            }

            // Force a redraw.
            NeedsDisplay = true;
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

        private void DrawRating(CGContext context, nfloat side, FilmRating rating)
        {
            DrawText(context, rating.ToString(), side/2, ScreeningsView.ScreeningControlLineHeight);
        }

        private void DrawAutomaticallyPlannedSymbol(CGContext context, nfloat side)
        {
            nfloat y = Screening is OnDemandScreening ? side*4/16 : 0;
            DrawText(context, AutomaticallyPlannedSymbol, side/2, y);
        }

        private static CGRect GetExtendedRect(CGRect screeningRect)
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

        #region Events
        public event EventHandler ScreeningSelected;

        internal void RaiseScreeningSelected()
        {
            ScreeningSelected?.Invoke(this, EventArgs.Empty);
        }
        #endregion
    }
}
