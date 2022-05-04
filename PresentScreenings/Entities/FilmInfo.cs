using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using System.Xml.Linq;
using AppKit;
using CoreText;
using Foundation;

namespace PresentScreenings.TableView
{
    public class FilmInfo
    {
        #region Public Enumerations.
        public enum ScreenedFilmType
        {
            PartOfCombinationProgram,
            ScreenedBefore,
            ScreenedAfter,
            DirectlyCombined
        }
        #endregion

        #region Public Nested Classes.
        public class ScreenedFilm
        {
            public int ScreenedFilmId { get; }
            public string Title { get; }
            public string Description { get; }
            public ScreenedFilmType ScreenedFilmType { get; }

            public ScreenedFilm(int screenedFilmId, string title, string description, ScreenedFilmType screenedFilmType)
            {
                ScreenedFilmId = screenedFilmId;
                Title = title;
                Description = description;
                ScreenedFilmType = screenedFilmType;
            }

            public override string ToString()
            {
                Film film = ViewController.GetFilmById(ScreenedFilmId);
                string titleText = $"{Title} ({film.MinutesString}) - {film.MaxRating}";
                return titleText + Environment.NewLine + Description;
            }
        }
        #endregion

        #region Private Members
        private static string _newLine = Environment.NewLine;
        private static string _twoLines = _newLine + _newLine;
        private static readonly Dictionary<string, ScreenedFilmType> _screenedFilmTypeByString;
        private static readonly Dictionary<ScreenedFilmType, string> _partByScreenedFilmType;
        private static readonly Dictionary<ScreenedFilmType, string> _headerByScreenedFilmType;
        private Dictionary<ScreenedFilmType, List<Film>> _combinationsByType = new Dictionary<ScreenedFilmType, List<Film>> { };
        #endregion

        #region Properties
        public int FilmId { get; }
        public string FilmDescription { get; }
        public string RawFilmDescription { get; }
        public NSAttributedString AttributedFilmDescription { get; }
        public string FilmArticle { get; }
        public List<int> CombinationProgramIds { get; private set; }
        public List<ScreenedFilm> ScreenedFilms { get; private set; }
        public WebUtility.MediumCategory MediumCategory => ViewController.GetFilmById(FilmId).Category;
        public string Url => ViewController.GetFilmById(FilmId).Url;
        public Film.FilmInfoStatus InfoStatus { get; }
        public static NSStringAttributes StandardAttributes { get; }
        #endregion

        #region Constructors
        static FilmInfo()
        {
            _screenedFilmTypeByString = new Dictionary<string, ScreenedFilmType> { };
            _screenedFilmTypeByString.Add("DIRECTLY_COMBINED", ScreenedFilmType.DirectlyCombined);
            _screenedFilmTypeByString.Add("PART_OF_COMBINATION_PROGRAM", ScreenedFilmType.PartOfCombinationProgram);
            _screenedFilmTypeByString.Add("SCREENED_AFTER", ScreenedFilmType.ScreenedAfter);
            _screenedFilmTypeByString.Add("SCREENED_BEFORE", ScreenedFilmType.ScreenedBefore);
            _partByScreenedFilmType = new Dictionary<ScreenedFilmType, string> { };
            _partByScreenedFilmType.Add(ScreenedFilmType.PartOfCombinationProgram, "Screened as part of");
            _partByScreenedFilmType.Add(ScreenedFilmType.ScreenedBefore, "Screened before");
            _partByScreenedFilmType.Add(ScreenedFilmType.ScreenedAfter, "Screened after");
            _partByScreenedFilmType.Add(ScreenedFilmType.DirectlyCombined, "Screened in combination with");
            _headerByScreenedFilmType = new Dictionary<ScreenedFilmType, string> { };
            _headerByScreenedFilmType.Add(ScreenedFilmType.PartOfCombinationProgram, "Screened films");
            _headerByScreenedFilmType.Add(ScreenedFilmType.ScreenedBefore, "Screened before the main feature");
            _headerByScreenedFilmType.Add(ScreenedFilmType.ScreenedAfter, "Screened after the main feature");
            _headerByScreenedFilmType.Add(ScreenedFilmType.DirectlyCombined, "Screened in combination with");
            StandardAttributes = new NSStringAttributes();
            StandardAttributes.Font = ControlsFactory.StandardFont;
            StandardAttributes.ForegroundColor = NSColor.Text;
        }

        public FilmInfo(int filmId, Film.FilmInfoStatus infoStatus, string description, string article)
        {
            FilmId = filmId;
            InfoStatus = infoStatus;
            RawFilmDescription = description;
            AttributedFilmDescription = HtmlToAttributed(description);
            FilmDescription = AttributedFilmDescription.Value;
            FilmArticle = article;
            CombinationProgramIds = new List<int> { };
            ScreenedFilms = new List<ScreenedFilm> { };
        }
        #endregion

        #region Override Methods
        public override string ToString()
        {
            return ToAttributedString().Value;
        }
        #endregion

        #region Public Methods
        public static List<FilmInfo> LoadFilmInfoFromXml(string path)
        {
            var filmInfos = new List<FilmInfo> { };
            XElement root;
            try
            {
                root = XElement.Load(path);
            }
            catch (FileNotFoundException)
            {
                return filmInfos;
            }
            catch (System.Exception)
            {
                return filmInfos;
            }
            var filmInfoElements =
                from el in root.Elements("FilmInfo")
                select
                (
                    (int)el.Attribute("FilmId"),
                    (string)el.Attribute("InfoStatus"),
                    (string)el.Attribute("FilmDescription"),
                    (string)el.Attribute("FilmArticle"),
                    from c in el.Element("CombinationPrograms").Elements("CombinationProgram")
                    select
                    (
                        (int)c.Attribute("CombinationProgramId")
                    ),
                    from s in el.Element("ScreenedFilms").Elements("ScreenedFilm")
                    select
                    (
                        (string)s.Attribute("ScreenedFilmId"),
                        (string)s.Attribute("Title"),
                        (string)s.Attribute("Description"),
                        (string)s.Attribute("ScreenedFilmType")
                    )
                );
            foreach (var filmInfoElement in filmInfoElements)
            {
                var filmInfo = new FilmInfo
                (
                    filmInfoElement.Item1,
                    StringToFilmInfoStatus(filmInfoElement.Item2),
                    filmInfoElement.Item3,
                    filmInfoElement.Item4
                );
                foreach (var compilationProgramAttribute in filmInfoElement.Item5)
                {
                    filmInfo.CombinationProgramIds.Add(compilationProgramAttribute);
                }
                foreach (var screenedFilmAttribute in filmInfoElement.Item6)
                {
                    int filmid = int.Parse(screenedFilmAttribute.Item1);
                    var title = screenedFilmAttribute.Item2;
                    var description = screenedFilmAttribute.Item3;
                    var type = screenedFilmAttribute.Item4;
                    var screenedFilmType = _screenedFilmTypeByString[type];
                    filmInfo.AddScreenedFilm(filmid, title, description, screenedFilmType);
                }
                filmInfos.Add(filmInfo);
            }
            return filmInfos;
        }

        public NSAttributedString ToAttributedString()
        {
            // Initialize variables.
            var attrText = new NSMutableAttributedString();
            attrText.BeginEditing();

            // Provide attributes for the URL.
            AppendWebLinkToAttributedString(ref attrText, Url, Url);
            AppendToAttributedString(ref attrText, _newLine);

            // If present, add the short description.
            if (AttributedFilmDescription.Length > 0)
            {
                string text = _newLine + "Description" + _newLine;
                attrText.Append(new NSAttributedString(text, StandardAttributes));
                attrText.Append(AttributedFilmDescription);
            }

            // Add the more elaborated article.
            if (FilmArticle != string.Empty)
            {
                string text = _newLine + "Article" + _newLine + FilmArticle + _newLine;
                attrText.Append(new NSAttributedString(text, StandardAttributes));
            }

            // Add combination programs in which this film is screened.
            if (CombinationProgramIds.Count > 0)
            {
                AppendCombinationProgramToAttributedString(ref attrText);
            }

            // Add screened films if present.
            if (ScreenedFilms.Count > 0)
            {
                AppendScreenedFilmsToAttributedString(ref attrText);
            }

            // Finalize the attributed string.
            attrText.EndEditing();

            return attrText;
        }

        public string ScreenedFilmsTostring()
        {
            // Get the screened films as an attributed string, which is the
            // standard representation.
            var attrText = new NSMutableAttributedString();
            attrText.BeginEditing();
            AppendScreenedFilmsToAttributedString(ref attrText);
            attrText.EndEditing();

            // Return the string value.
            return attrText.Value;
        }

        public static NSAttributedString InfoString(Film film)
        {
            var filmInfo = ViewController.GetFilmInfo(film.FilmId);
            if (filmInfo == null)
            {
                return new NSAttributedString(string.Empty);
            }
            NSAttributedString text = filmInfo.AttributedFilmDescription;
            if (text.Length == 0)
            {
                text = new NSAttributedString(filmInfo.FilmArticle);
            }
            return text;
        }

        public string GetGenreDescription()
        {
            Match m;
            string genrePattern = @"^Genre: *(.*)$";
            m = Regex.Match(FilmArticle, genrePattern, RegexOptions.Multiline);
            if (m.Success)
            {
                return m.Result(@"$1");
            }
            return String.Empty;
        }
        #endregion

        #region Private Methods
        private static Film.FilmInfoStatus StringToFilmInfoStatus(string name)
        {
            try
            {
                return (Film.FilmInfoStatus)Enum.Parse(typeof(Film.FilmInfoStatus), name);
            }
            catch
            {
                throw new IllegalFilmInfoCategoryException($"'{name}' is not a valid FilmInfoCategory");
            }
        }

        private void AddScreenedFilm(int filmid, string title, string description, ScreenedFilmType screenedFilmType)
        {
            var screenedFilm = new ScreenedFilm(filmid, title, description, screenedFilmType);
            ScreenedFilms.Add(screenedFilm);
        }

        private NSAttributedString HtmlToAttributed(string text)
        {
            var html = text + Environment.NewLine;
            int startIndex = 0;
            var attributedString = new NSMutableAttributedString(html);

            attributedString.BeginEditing();

            // Initialize with the standard attributes.
            NSRange range = new NSRange(0, html.Length);
            attributedString.AddAttributes(StandardAttributes, range);

            // Set attributes for the HTML indicated ranges.
            while (startIndex >= 0)
            {
                startIndex = NextAttributedPart(ref attributedString, startIndex);
            }

            attributedString.EndEditing();

            return attributedString;
        }

        /// <summary>
        /// Search for HTML tags, remove them and apply a bold font
        /// to the text range marked by the tags.
        ///
        /// It is presumed that:
        ///     - Every start tag has a matching end tag
        ///     - Tag ranges do not overlap
        /// </summary>
        /// <param name="attrText"> The attributed string to be searched from</param>
        /// <param name="index">The index to start searching</param>
        /// <returns>The new starting index, -1 when no tags are found.</returns>
        private static int NextAttributedPart(ref NSMutableAttributedString attrText, int index)
        {
            // Search for an html tag.
            string text = attrText.Value;
            int startIndex = text.IndexOf("<", index);
            if (startIndex >= 0)
            {
                int startIndex1 = startIndex;
                int endIndex1 = text.IndexOf(">", startIndex);
                attrText.DeleteRange(new NSRange(startIndex1, endIndex1 - startIndex + 1));
                text = attrText.Value;

                // Find the closing tag.
                int startIndex2 = text.IndexOf("<", startIndex);
                if (text.Substring(startIndex2 + 1, 1) == "/")
                {
                    int endIndex2 = text.IndexOf(">", startIndex2);
                    attrText.DeleteRange(new NSRange(startIndex2, endIndex2 - startIndex2 + 1));
                    var range = new NSRange(startIndex1, startIndex2 - startIndex1);
                    attrText.AddAttribute(CTStringAttributeKey.Font, ControlsFactory.StandardBoldFont, range);
                    startIndex = startIndex2;
                }
            }
            return startIndex;
        }

        private void AppendCombinationProgramToAttributedString(ref NSMutableAttributedString attrText)
        {
            // Initialize the dictionary that keeps all combination programs
            // by type.
            SetCombinationsByType();

            // Per type, append the applicable header and the combination
            // programs in which this film has that type to the given string.
            string space = _newLine;
            foreach (var screenedFilmType in _combinationsByType.Keys)
            {
                AppendToAttributedString(ref attrText, $"{space}{_partByScreenedFilmType[screenedFilmType]}:");
                foreach (var combiProgram in _combinationsByType[screenedFilmType])
                {
                    AppendToAttributedString(ref attrText, _newLine);
                    AppendFilmLinkToAtrributedString(ref attrText, combiProgram);
                }
                space = _twoLines;
            }
        }

        private void AppendScreenedFilmsToAttributedString(ref NSMutableAttributedString attrText)
        {
            // Create a list of the distinct screened film types in the
            // screened films.
            var screenedFilmTypes = ScreenedFilms
                .Select(sf => sf.ScreenedFilmType)
                .Distinct();

            // Per type, append the applicible header and the screened films
            // with that type to the given string.
            var space = _newLine;
            foreach (var screenedFilmType in screenedFilmTypes)
            {
                AppendToAttributedString(ref attrText, $"{space}{_headerByScreenedFilmType[screenedFilmType]}:");
                var screenedFilmsOfType = ScreenedFilms
                    .Where(sf => sf.ScreenedFilmType == screenedFilmType);
                foreach (ScreenedFilm screenedFilm in screenedFilmsOfType)
                {
                    Film film = ViewController.GetFilmById(screenedFilm.ScreenedFilmId);
                    AppendToAttributedString(ref attrText, space);
                    AppendFilmLinkToAtrributedString(ref attrText, film);
                    AppendToAttributedString(ref attrText, _newLine + screenedFilm.Description);
                    space = _twoLines;
                }
            }

            // Calculate the average rating of all screened films if applicable.
            decimal meanRating = TimeWeightedMeanRating();
            if (meanRating != decimal.Zero)
            {
                AppendToAttributedString(ref attrText, $"{_twoLines}Time weighted mean rating: {meanRating:0.##}");
            }
        }

        private void AppendToAttributedString(ref NSMutableAttributedString attrText, string text)
        {
            attrText.Append(new NSAttributedString(text, StandardAttributes));
        }

        private void AppendFilmLinkToAtrributedString(ref NSMutableAttributedString attrText, Film film)
        {
            AppendWebLinkToAttributedString(ref attrText, film.Url, film.Title);
            AppendToAttributedString(ref attrText, $" ({film.MinutesString}) - {film.MaxRating}");
        }

        private void AppendWebLinkToAttributedString(ref NSMutableAttributedString attrText, string url, string display)
        {
            var range = new NSRange(attrText.Length, display.Length);
            var attributes = new NSStringAttributes();
            attributes.ForegroundColor = NSColor.SystemBlue;
            attributes.SetUnderlineStyle(NSUnderlineStyle.Single);
            attributes.LinkUrl = new NSUrl(url);
            attributes.Cursor = NSCursor.PointingHandCursor;
            AppendToAttributedString(ref attrText, display);
            attrText.AddAttributes(attributes, range);
        }

        private void SetCombinationsByType()
        {
            if (CombinationProgramIds.Count > 0)
            {
                // Per combination program, find its screened film that matches
                // the current film and create a list of combination program -
                // screened film pairs.
                var combinationScreenedPairs = CombinationProgramIds
                    .Select(i => ViewController.GetFilmById(i))
                    .SelectMany(cf => cf.FilmInfo.ScreenedFilms
                        .Select(sf => new { cf, sf })
                        .Where(pair => pair.sf.ScreenedFilmId == FilmId));

                // Store each screened film type together with the combination
                // programs it is paired with.
                _combinationsByType = new Dictionary<ScreenedFilmType, List<Film>> { };
                foreach (var pair in combinationScreenedPairs)
                {
                    if (!_combinationsByType.Keys.Contains(pair.sf.ScreenedFilmType))
                    {
                        _combinationsByType.Add(pair.sf.ScreenedFilmType, new List<Film> { });
                    }
                    _combinationsByType[pair.sf.ScreenedFilmType].Add(pair.cf);
                }
            }
        }

        private decimal TimeWeightedMeanRating()
        {
            TimeSpan time = TimeSpan.Zero;
            decimal ratingMinutes = 0M;
            decimal minutesSum = 0M;
            bool fullyRated = true;
            foreach (var screenedFilm in ScreenedFilms)
            {
                Film film = ViewController.GetFilmById(screenedFilm.ScreenedFilmId);
                FilmRating rating = film.MaxRating;
                if (rating.IsUnrated)
                {
                    fullyRated = false;
                    break;
                }
                decimal decimalRating = decimal.Parse(rating.Value);
                decimal minutes = (decimal)film.Duration.TotalMinutes;
                ratingMinutes += decimalRating * minutes;
                minutesSum += minutes;
            }
            if (fullyRated && ScreenedFilms.Count > 1)
            {
                decimal meanRating = ratingMinutes / minutesSum;
                return meanRating;
            }
            return decimal.Zero;
        }
        #endregion
    }
}
