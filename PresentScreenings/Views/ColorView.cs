using System.Collections.Generic;
using System;
using AppKit;
using CoreGraphics;

namespace PresentScreenings.TableView
{
    /// <summary>
    /// Color view, provides the dedicated color for representation of a screening.
    /// </summary>
    /// 
    /// Could be refactored as to work with color-pairs (text-backgound).

    public static class ColorView
    {
        #region Private members
        static NSColor screeningTextColorBlack;
        static NSColor screeningBGColorBlack;
        static NSColor screeningTextColorGrey;
        static NSColor screeningBGColorGrey;
        static NSColor screeningTextColorBlue;
        static NSColor screeningBGColorBlue;
        static NSColor screeningTextColorRed;
        static NSColor screeningBGColorRed;
        static NSColor screeningTextColorPurple;
        static NSColor screeningBGColorPurple;
        static NSColor screeningTextColorAqua;
        static NSColor screeningBGColorAqua;
        static readonly Dictionary<ScreeningStatus.Status, NSColor> screeningTextColor;
        static readonly Dictionary<ScreeningStatus.Status, NSColor> screeningBGColor;
        static readonly Dictionary<ScreeningStatus.TicketsStatus, NSColor> ticketsStatusColor;
        static NSColor ClickPadColorBlue = NSColor.FromRgba(0, 0, 255, 207);
        static NSColor ClickPadColorGrey = NSColor.FromRgba(127, 127, 127, 119);
        static NSColor ClickPadTextColorSelected = NSColor.White;
        static NSColor ClickPadTextColorUnselected = NSColor.Red;
        static NSColor soldOutColorSelected = NSColor.FromRgb(219, 176, 38);
        static NSColor soldOutColorUnselected = NSColor.FromRgb(176, 79, 38);
        #endregion

        #region Public Properties
        #endregion

        #region Constructors
        static ColorView()
        {
            screeningBGColorBlack = NSColor.FromRgb(0, 0, 0);
            screeningTextColorBlack = NSColor.White;
            screeningBGColorGrey = NSColor.FromRgb(219, 219, 219);
            screeningTextColorGrey = NSColor.FromRgb(0, 0, 0);
            screeningBGColorBlue = NSColor.FromRgb(0, 38, 176);
            screeningTextColorBlue = NSColor.FromRgb(255, 255, 255);
            screeningBGColorRed = NSColor.FromRgb(176, 0, 38);
            screeningTextColorRed = NSColor.White;
            screeningBGColorPurple = NSColor.FromRgb(176, 0, 176);
            screeningTextColorPurple = NSColor.White;
            screeningBGColorAqua = NSColor.FromRgb(38, 255, 176);
            screeningTextColorAqua = NSColor.Black;

            screeningTextColor = new Dictionary<ScreeningStatus.Status, NSColor> { };
            screeningTextColor.Add(ScreeningStatus.Status.Free, screeningTextColorBlack);
            screeningTextColor.Add(ScreeningStatus.Status.NeedingTickets, screeningTextColorPurple);
            screeningTextColor.Add(ScreeningStatus.Status.Attending, screeningTextColorRed);
            screeningTextColor.Add(ScreeningStatus.Status.AttendedByFriend, screeningTextColorBlue);
            screeningTextColor.Add(ScreeningStatus.Status.AttendingFilm, screeningTextColorGrey);
            screeningTextColor.Add(ScreeningStatus.Status.TimeOverlap, screeningTextColorGrey);

            screeningBGColor = new Dictionary<ScreeningStatus.Status, NSColor> { };
            screeningBGColor.Add(ScreeningStatus.Status.Free, screeningBGColorBlack);
            screeningBGColor.Add(ScreeningStatus.Status.NeedingTickets, screeningBGColorPurple);
            screeningBGColor.Add(ScreeningStatus.Status.Attending, screeningBGColorRed);
            screeningBGColor.Add(ScreeningStatus.Status.AttendedByFriend, screeningBGColorBlue);
            screeningBGColor.Add(ScreeningStatus.Status.AttendingFilm, NSColor.Yellow);
            screeningBGColor.Add(ScreeningStatus.Status.TimeOverlap, screeningBGColorGrey);

            ticketsStatusColor = new Dictionary<ScreeningStatus.TicketsStatus, NSColor> { };
            ticketsStatusColor.Add(ScreeningStatus.TicketsStatus.TicketsArranged, screeningBGColorRed);
            ticketsStatusColor.Add(ScreeningStatus.TicketsStatus.NoTicketsNeeded, screeningBGColorBlack);
            ticketsStatusColor.Add(ScreeningStatus.TicketsStatus.MustBuyTickets, screeningBGColorPurple);
            ticketsStatusColor.Add(ScreeningStatus.TicketsStatus.MustSellTickets, screeningBGColorAqua);
        }
        #endregion

        #region Public members
        public static void SetScreeningColor(Screening screening, NSTextField label)
        {
            var status = screening.Status;
            label.BackgroundColor = screeningBGColor[status];
            label.TextColor = screeningTextColor[status];
        }

        public static void SetScreeningColor(Screening screening, CGContext context)
        {
            var status = screening.Status;
            context.SetFillColor(screeningBGColor[status].CGColor);
            context.SetStrokeColor(screeningTextColor[status].CGColor);
        }

        public static void SetScreeningColor(Screening screening, CGContext context, bool textMode)
        {
            var status = screening.Status;
            if (textMode)
            {
                context.SetFillColor(screeningTextColor[status].CGColor);
                context.SetStrokeColor(screeningTextColor[status].CGColor);
            }
            else
            {
                SetScreeningColor(screening, context);
            }
        }

        public static void SetTicketsStatusColor(Screening screening, CGContext context)
        {
            var status = screening.TicketStatus;
            NSColor color = ticketsStatusColor[status];
            context.SetStrokeColor(color.CGColor);
        }

        public static NSColor ClickPadBackgroundColor(bool selected)
        {
            return selected ? ClickPadColorBlue : ClickPadColorGrey;
        }

        public static NSColor ClickPadTextColor(bool selected)
        {
            return selected ? ClickPadTextColorSelected : ClickPadTextColorUnselected;
        }

        public static NSColor SoldOutColor(bool selected)
        {
            return selected ? soldOutColorSelected : soldOutColorUnselected;
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

        public static void DrawTicketAvalabilityFrame(CGContext g, Screening screening, CGRect rect)
        {
            g.SetLineWidth(2);
            SetTicketsStatusColor(screening, g);
            var rectPath = new CGPath();
            nfloat org = 1;
            nfloat x = rect.Width - 2 * org;
            nfloat y = rect.Height - 2 * org;
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

        public static void DrawTicketAvalabilityFrame(CGContext g, Screening screening, nfloat side)
        {
            DrawTicketAvalabilityFrame(g, screening, new CGRect(0, 0, side, side));
        }
        #endregion
    }
}
