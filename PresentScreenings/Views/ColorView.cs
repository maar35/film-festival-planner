using System.Collections.Generic;
using System;
using AppKit;
using CoreGraphics;
using CoreText;
using Foundation;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Color view, provides the dedicated colors for representation of a screening.
    /// </summary>
    /// 
    /// Could be refactored as to work with color-pairs (text-backgound).

    public static class ColorView
    {
        #region Public Nested Classes.
        class WebColor : ListStreamer
        {
            #region Properties
            public string Name { get; private set; }
            public string Code { get; private set; }
            #endregion

            #region Constructors
            // Empty constructor to facilitate ListStreamer method calls.
            public WebColor() { }

            // Constructor to read records from the interface file.
            public WebColor(string screenText)
            {
                string[] fields = screenText.Split(';');
                Name = fields[0];
                Code = fields[1];
            }
            #endregion

            #region Override Methods
            public override bool ListFileHasHeader()
            {
                return false;
            }
            #endregion
        }
        #endregion

        #region Private members
        private static readonly NSColor screeningBgColorBlack = NSColor.FromRgb(0, 0, 0);
        private static readonly NSColor screeningTextColorBlack = NSColor.White;
        private static readonly NSColor screeningBgColorOffBlack = NSColor.FromRgb(38, 38, 38);
        private static readonly NSColor screeningTextColorOffBlack = NSColor.Orange;
        private static readonly NSColor screeningBgColorGrey = NSColor.FromRgb(219, 219, 219);
        private static readonly NSColor screeningTextColorGrey = NSColor.FromRgb(0, 0, 0);
        private static readonly NSColor screeningBgColorDarkGrey = NSColor.FromRgb(176, 176, 176);
        private static readonly NSColor screeningTextColorDarkGrey = NSColor.FromRgb(0, 0, 0);
        private static readonly NSColor screeningBgColorBlue = NSColor.FromRgb(0, 38, 176);
        private static readonly NSColor screeningTextColorBlue = NSColor.FromRgb(255, 255, 255);
        private static readonly NSColor screeningBgColorRed = NSColor.FromRgb(176, 0, 38);
        private static readonly NSColor screeningTextColorRed = NSColor.White;
        private static readonly NSColor screeningBgColorPurple = NSColor.FromRgb(176, 0, 176);
        private static readonly NSColor screeningTextColorPurple = NSColor.White;
        private static readonly NSColor screeningBgColorAqua = NSColor.FromRgb(38, 255, 176);
        private static readonly NSColor screeningTextColorAqua = NSColor.Black;
        private static readonly Dictionary<ScreeningInfo.ScreeningStatus, NSColor> TextColorByScreeningStatus;
        private static readonly Dictionary<ScreeningInfo.ScreeningStatus, NSColor> BgColorByScreeningStatus;
        private static readonly Dictionary<ScreeningInfo.TicketsStatus, NSColor> ColorByTicketStatus;
        private static readonly NSColor ClickPadColorBlue = NSColor.FromRgba(0, 0, 255, 207);
        private static readonly NSColor ClickPadColorGrey = NSColor.FromRgba(127, 127, 127, 119);
        private static readonly NSColor ClickPadBgColorSelected = ClickPadColorBlue;
        private static readonly NSColor ClickPadBgColorUnselected = ClickPadColorGrey;
        private static readonly NSColor ClickPadTextColorSelected = NSColor.White;
        private static readonly NSColor ClickPadTextColorUnselected = NSColor.Red;
        private static readonly NSColor soldOutColorSelected = NSColor.FromRgb(219, 176, 38);
        private static readonly NSColor soldOutColorUnselected = NSColor.FromRgb(176, 79, 38);
        private static readonly NSColor _warningBackgroundColor = NSColor.FromRgb(255, 242, 0);
        private static CTStringAttributes _stringAttributes;
        private static string _automaticallyPlannedSymbol = ControlsFactory.AutomaticallyPlannedSymbol;
        private const float _clickpadMinSideToDrawAll = ControlsFactory.ClickpadMinSideToDrawAllElements;
        private const float _clickpadRightMargin = ControlsFactory.ClickpadRightMargin;
        private const float _clickpadTopMargin = ControlsFactory.ClickpadTopMargin;
        private const float _labelLineHeight = ControlsFactory.LabelLineHeight;
        private const float _horizontalTextOffset = -1;
        private const float _verticalTextOffset = ControlsFactory.VerticalTextOffset;
        private const float _progressNeedleMargin = 2;
        private const int _maxDaysInRuler = 5;
        #endregion

        #region Properties
        public static NSColor WarningBackgroundColor => _warningBackgroundColor;
        public static Dictionary<string, NSColor> ColorByName { get; set; }
        #endregion

        #region Constructors
        static ColorView()
        {
            SetWebColors();

            TextColorByScreeningStatus = new Dictionary<ScreeningInfo.ScreeningStatus, NSColor> { };
            TextColorByScreeningStatus.Add(ScreeningInfo.ScreeningStatus.Free, screeningTextColorBlack);
            TextColorByScreeningStatus.Add(ScreeningInfo.ScreeningStatus.Unavailable, screeningTextColorOffBlack);
            TextColorByScreeningStatus.Add(ScreeningInfo.ScreeningStatus.NeedingTickets, screeningTextColorPurple);
            TextColorByScreeningStatus.Add(ScreeningInfo.ScreeningStatus.Attending, screeningTextColorRed);
            TextColorByScreeningStatus.Add(ScreeningInfo.ScreeningStatus.AttendedByFriend, screeningTextColorBlue);
            TextColorByScreeningStatus.Add(ScreeningInfo.ScreeningStatus.AttendingFilm, screeningTextColorGrey);
            TextColorByScreeningStatus.Add(ScreeningInfo.ScreeningStatus.TimeOverlap, screeningTextColorGrey);
            TextColorByScreeningStatus.Add(ScreeningInfo.ScreeningStatus.NoTravelTime, screeningTextColorDarkGrey);

            BgColorByScreeningStatus = new Dictionary<ScreeningInfo.ScreeningStatus, NSColor> { };
            BgColorByScreeningStatus.Add(ScreeningInfo.ScreeningStatus.Free, screeningBgColorBlack);
            BgColorByScreeningStatus.Add(ScreeningInfo.ScreeningStatus.Unavailable, screeningBgColorOffBlack);
            BgColorByScreeningStatus.Add(ScreeningInfo.ScreeningStatus.NeedingTickets, screeningBgColorPurple);
            BgColorByScreeningStatus.Add(ScreeningInfo.ScreeningStatus.Attending, screeningBgColorRed);
            BgColorByScreeningStatus.Add(ScreeningInfo.ScreeningStatus.AttendedByFriend, screeningBgColorBlue);
            BgColorByScreeningStatus.Add(ScreeningInfo.ScreeningStatus.AttendingFilm, NSColor.Yellow);
            BgColorByScreeningStatus.Add(ScreeningInfo.ScreeningStatus.TimeOverlap, screeningBgColorGrey);
            BgColorByScreeningStatus.Add(ScreeningInfo.ScreeningStatus.NoTravelTime, screeningBgColorDarkGrey);

            ColorByTicketStatus = new Dictionary<ScreeningInfo.TicketsStatus, NSColor> { };
            ColorByTicketStatus.Add(ScreeningInfo.TicketsStatus.TicketsArranged, screeningBgColorRed);
            ColorByTicketStatus.Add(ScreeningInfo.TicketsStatus.NoTicketsNeeded, screeningBgColorBlack);
            ColorByTicketStatus.Add(ScreeningInfo.TicketsStatus.MustBuyTickets, screeningBgColorPurple);
            ColorByTicketStatus.Add(ScreeningInfo.TicketsStatus.MustSellTickets, screeningBgColorAqua);
        }
        #endregion

        #region Public Methods working with colors
        public static void SetScreeningColor(Screening screening, NSTextField label)
        {
            var status = screening.Status;
            label.BackgroundColor = BgColorByScreeningStatus[status];
            label.TextColor = TextColorByScreeningStatus[status];
        }

        public static void SetScreeningColor(Screening screening, CGContext context)
        {
            var status = screening.Status;
            context.SetFillColor(BgColorByScreeningStatus[status].CGColor);
            context.SetStrokeColor(TextColorByScreeningStatus[status].CGColor);
        }

        public static void SetScreeningColor(Screening screening, CGContext context, bool textMode)
        {
            var status = screening.Status;
            if (textMode)
            {
                context.SetFillColor(TextColorByScreeningStatus[status].CGColor);
                context.SetStrokeColor(TextColorByScreeningStatus[status].CGColor);
            }
            else
            {
                SetScreeningColor(screening, context);
            }
        }

        public static void SetTicketsStatusColor(Screening screening, CGContext context)
        {
            var status = screening.TicketStatus;
            NSColor color = ColorByTicketStatus[status];
            context.SetStrokeColor(color.CGColor);
        }

        public static NSColor ClickPadBackgroundColor(bool selected)
        {
            return selected ? ClickPadBgColorSelected : ClickPadBgColorUnselected;
        }

        public static NSColor ClickPadTextColor(bool selected)
        {
            return selected ? ClickPadTextColorSelected : ClickPadTextColorUnselected;
        }

        public static NSColor SoldOutColor(bool selected)
        {
            return selected ? soldOutColorSelected : soldOutColorUnselected;
        }
        #endregion

        #region Public Methods that draw on click pads
        public static void DrawStandardClickpad(CGContext context, Screening screening, CGRect frame, bool selected)
        {
            // Assume the frame is a square.
            var side = frame.Height;

            // Color the control surface.
            DrawClickPad(context, frame, selected);

            // Draw a frame if something's wrong with the tickets.
            if (ScreeningInfo.TicketStatusNeedsAttention(screening))
            {
                DrawTicketAvalabilityFrame(context, screening, side);
            }

            // Draw a progress bar if the screening is on-demand.
            if (screening is OnDemandScreening onDemandScreening)
            {
                DrawOnDemandAvailabilityStatus(context, onDemandScreening, side, selected);
            }

            // Draw the Sold Out symbol.
            if (screening.SoldOut)
            {
                DrawSoldOutSymbol(context, selected, frame);
            }

            // Draw a warning symbol if feasible.
            if (screening.Warning != ScreeningInfo.Warning.NoWarning)
            {
                DrawWarningMiniature(context, side);
            }

            // Switch context to text drawing.
            InitializeCoreText(context, selected, side);

            // Draw the Automatically Planned symbol.
            if (screening.AutomaticallyPlanned)
            {
                DrawAutomaticallyPlannedSymbol(context, screening, side);
            }

            // Draw the rating of the film.
            DrawRating(context, screening, side);
        }

        private static void DrawClickPad(CGContext context, CGRect clickRect, bool Selected)
        {
            var gpath = new CGPath();
            gpath.AddRect(clickRect);
            ClickPadBackgroundColor(Selected).SetFill();
            gpath.CloseSubpath();
            context.AddPath(gpath);
            context.DrawPath(CGPathDrawingMode.Fill);
        }

        public static void DrawSoldOutSymbol(CGContext g, bool selected, CGRect rect)
        {
            var path = new CGPath();
            nfloat margin = rect.Width * 3 / 16;
            nfloat side = (nfloat)Math.Min((double)rect.Height, (double)rect.Width) - 2 * margin;
            g.SetLineWidth(2);
            SoldOutColor(selected).SetStroke();
            var diagonalLeftTopToRightBottom = new CGPath();
            diagonalLeftTopToRightBottom.AddLines(new CGPoint[]{
                new CGPoint(margin, margin + side),
                new CGPoint(margin + side, margin)
            });
            diagonalLeftTopToRightBottom.CloseSubpath();
            g.AddPath(diagonalLeftTopToRightBottom);
            var diagonalLeftBottomToRightTop = new CGPath();
            diagonalLeftBottomToRightTop.AddLines(new CGPoint[]{
                new CGPoint(margin, margin),
                new CGPoint(margin + side, margin + side)
            });
            diagonalLeftBottomToRightTop.CloseSubpath();
            g.AddPath(diagonalLeftBottomToRightTop);
            g.DrawPath(CGPathDrawingMode.Stroke);
        }

        public static void DrawTicketAvalabilityFrame(CGContext g, Screening screening, nfloat side)
        {
            g.SetLineWidth(2);
            SetTicketsStatusColor(screening, g);
            var rectPath = new CGPath();
            nfloat org = 1;
            nfloat x = side - 2 * org;
            nfloat y = side - 2 * org;
            rectPath.AddLines(new CGPoint[]{
                new CGPoint(org, y),
                new CGPoint(x, y),
                new CGPoint(x, org),
                new CGPoint(org, org)
            });
            rectPath.CloseSubpath();
            g.AddPath(rectPath);
            g.DrawPath(CGPathDrawingMode.Stroke);
        }

        public static void DrawOnDemandAvailabilityStatus(CGContext context, OnDemandScreening screening, nfloat side, bool selected)
        {
            // Establish some base dimensions.
            var margin = _progressNeedleMargin;
            nfloat w = side - 2 * margin;
            nfloat h = side - 2 * margin;
            nfloat x = margin;
            nfloat y = margin;
            var windowSeconds = (screening.WindowEndTime - screening.WindowStartTime).TotalSeconds;
            var passedSeconds = (screening.StartTime - screening.WindowStartTime).TotalSeconds;
            nfloat wPassed = w * (nfloat)passedSeconds / (nfloat)windowSeconds;
            nfloat wLeft = w - wPassed;

            // Initlialize core graphics settings.
            context.SetStrokeColor(ClickPadTextColor(selected).CGColor);
            context.SetLineWidth(1);

            // Draw the passed time part of the progres bar.
            using (var passedPath = new CGPath())
            {
                context.SetFillColor(ClickPadTextColor(selected).CGColor);
                passedPath.AddRect(new CGRect(x, y + h * 1 / 16, wPassed, h * 2 / 16));
                passedPath.CloseSubpath();
                context.AddPath(passedPath);
            }
            context.DrawPath(CGPathDrawingMode.FillStroke);

            // Draw the left time part of the progress bar.
            using (var leftPath = new CGPath())
            {
                context.SetFillColor((selected ? ClickPadBackgroundColor(selected) : NSColor.White).CGColor);
                leftPath.AddRect(new CGRect(x + wPassed, y + h * 1 / 16, wLeft, h * 2 / 16));
                leftPath.CloseSubpath();
                context.AddPath(leftPath);
            }
            context.DrawPath(CGPathDrawingMode.FillStroke);

            // Draw verticle needle lines to indicate availability days.
            var daySeconds = ViewController.DaySpan.TotalSeconds;
            nfloat days = (nfloat)windowSeconds / (nfloat)daySeconds;
            nfloat wPeriod = w / days;
            if (days <= _maxDaysInRuler)
            {
                using (var needlePath = new CGPath())
                {
                    for (int i = 1; i < days; i++)
                    {
                        needlePath.AddLines(new CGPoint[]
                        {
                            new CGPoint(i*wPeriod, y + h*1/16),
                            new CGPoint(i*wPeriod, y + h*3/16)
                        });
                    }
                    context.AddPath(needlePath);
                }
            }
            context.DrawPath(CGPathDrawingMode.FillStroke);
        }

        public static void DrawWarningMiniature(CGContext context, nfloat side)
        {
            if (side >= _clickpadMinSideToDrawAll)
            {
                nfloat x = side * 1 / 16;
                nfloat y = side * 4 / 16;
                context.SetLineWidth(1);
                NSColor.Black.SetStroke();
                WarningBackgroundColor.SetFill();
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
        }

        public static void InitializeCoreText(CGContext context, bool selected, nfloat side)
        {
            context.TranslateCTM(_horizontalTextOffset, _verticalTextOffset);
            NSColor textColor = ClickPadTextColor(selected);
            context.SetTextDrawingMode(CGTextDrawingMode.Fill);
            context.SetFillColor(textColor.CGColor);
            _stringAttributes = new CTStringAttributes
            {
                ForegroundColorFromContext = true,
                Font = ControlsFactory.StandardCtBoldFont,
            };
        }

        public static void DrawRating(CGContext context, Screening screening, nfloat side)
        {
            if (side >=_clickpadMinSideToDrawAll)
            {
                var film = ViewController.GetFilmById(screening.FilmId);
                var rating = ViewController.GetMaxRating(film);
                if (rating.IsGreaterOrEqual(FilmRating.LowestSuperRating) || rating.Equals(FilmRating.Unrated))
                {
                    var x = side - _clickpadRightMargin;
                    var y = side - _clickpadTopMargin - _labelLineHeight;
                    DrawText(context, rating.ToString(), x, y);
                }
            }
        }

        public static void DrawAutomaticallyPlannedSymbol(CGContext context, Screening screening, nfloat side)
        {
            if (side >= _clickpadMinSideToDrawAll)
            {
                var x = side - _clickpadRightMargin;
                var yUnmovable = side - _clickpadTopMargin - 2 * _labelLineHeight;
                var yMovable = side * 4 / 16;
                var y = screening is OnDemandScreening ? yMovable : yUnmovable;
                DrawText(context, _automaticallyPlannedSymbol, x, y);
            }
            else
            {
                var x = side / 3;
                var y = side - _labelLineHeight;
                DrawText(context, _automaticallyPlannedSymbol, x, y);
            }
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

        public static NSColor GetColor(string colorCode)
        {
            NSColor color = null;
            if (colorCode.StartsWith("#"))
            {
                var r = Convert.ToInt32(colorCode.Substring(1, 2), 16);
                var g = Convert.ToInt32(colorCode.Substring(3, 2), 16);
                var b = Convert.ToInt32(colorCode.Substring(5, 2), 16);
                color = NSColor.FromRgb(r, g, b);
            }
            return color;
        }

        public static void SetWebColors()
        {
            // Read web colors.
            var webColors = new WebColor().ReadListFromFile(AppDelegate.WebColorsFile, line => new WebColor(line));

            // Fill the dictionary.
            ColorByName = new Dictionary<string, NSColor> { };
            foreach (var webColor in webColors)
            {
                ColorByName.Add(webColor.Name.ToLower(), GetColor(webColor.Code));
            }
        }
        #endregion
    }
}
