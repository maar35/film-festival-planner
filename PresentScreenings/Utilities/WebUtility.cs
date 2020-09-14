using System;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;

namespace PresentScreenings.TableView
{
    public static class WebUtility
    {
        #region Public Members
        public enum MediumCatagory
        {
            Films,
            CombinedProgrammes,
            Events
        }

        public enum ParseInfoType
        {
            Description,
            Article,
            ScreenedFilms
        }
        #endregion

        #region Private Variables
        struct ParseInfo
        {
            public ParseInfoType type;
            public string description;
            public Regex re;
            public Regex filterRe;
            public string filterReplacement;
        }
        static Dictionary<MediumCatagory, List<ParseInfo>> _parseInfoByCatagory;
        #endregion

        #region Properties
        static public Dictionary<MediumCatagory, string> FolderByCatagory;
        #endregion

        #region Constructors
        static WebUtility()
        {
            FolderByCatagory = new Dictionary<MediumCatagory, string> { };
            FolderByCatagory[MediumCatagory.Films] = "films";
            FolderByCatagory[MediumCatagory.CombinedProgrammes] = "verzamelprogrammas";
            FolderByCatagory[MediumCatagory.Events] = "events";
            var descriptionParseInfo = new ParseInfo
            {
                type = ParseInfoType.Description,
                description = "Description",
                re = new Regex(@"\<meta name=""description"" content=""(.*)"" />")
            };
            var articleParseInfo = new ParseInfo
            {
                type = ParseInfoType.Article,
                description = "Article",
                re = new Regex(@"\<article.*?(\<p\>.*\</p\>)\s*\</div\>", RegexOptions.Singleline)
            };
            var screenedFilmsParseInfo = new ParseInfo
            {
                type = ParseInfoType.ScreenedFilms,
                description = "Screened films",
                re = new Regex(@"\<section class=""rectangle-column""\>\s*\<h2\>(.*?)\</h2\>\s*\<span class=""hover-info""\>.*?\<p class=""full-text""\>(.*?)\</p\>", RegexOptions.Singleline),
                filterRe = new Regex(@"^(.*)(\<main.*\</main\>)(.*)$", RegexOptions.Singleline),
                filterReplacement = @"$2"
            };
            _parseInfoByCatagory = new Dictionary<MediumCatagory, List<ParseInfo>> { };
            _parseInfoByCatagory[MediumCatagory.Films] = new List<ParseInfo> { descriptionParseInfo, articleParseInfo };
            _parseInfoByCatagory[MediumCatagory.Events] = new List<ParseInfo> { articleParseInfo };
            _parseInfoByCatagory[MediumCatagory.CombinedProgrammes] = new List<ParseInfo> { articleParseInfo, screenedFilmsParseInfo };
        }
        #endregion

        #region Private Methods
        #endregion

        #region Public Methods

        /// <summary>
        /// Html to plain text.
        /// By Ben Anderson (https://stackoverflow.com/questions/286813/how-do-you-convert-html-to-plain-text)
        /// </summary>
        /// <returns>The plain text.</returns>
        /// <param name="html">Html.</param>
        public static string HtmlToPlainText(string html)
        {
            const string tagWhiteSpace = @"(>|$)(\W|\n|\r)+<";//matches one or more (white space or line breaks) between '>' and '<'
            const string stripFormatting = @"<[^>]*(>|$)";//match any character between '<' and '>', even when end tag is missing
            const string lineBreak = @"<(br|BR)\s{0,1}\/{0,1}>";//matches: <br>,<br/>,<br />,<BR>,<BR/>,<BR />
            var lineBreakRegex = new Regex(lineBreak, RegexOptions.Multiline);
            var stripFormattingRegex = new Regex(stripFormatting, RegexOptions.Multiline);
            var tagWhiteSpaceRegex = new Regex(tagWhiteSpace, RegexOptions.Multiline);

            var text = html;
            //Decode html specific characters
            text = System.Net.WebUtility.HtmlDecode(text);
            //Remove tag whitespace/line breaks
            text = tagWhiteSpaceRegex.Replace(text, "><");
            //Replace <br /> with line breaks
            text = lineBreakRegex.Replace(text, Environment.NewLine);
            //Strip formatting
            text = stripFormattingRegex.Replace(text, string.Empty);

            return text;
        }

        public static string HtmlToText(string html)
        {
            return Screening.HtmlDecode(HtmlToPlainText(html));
        }

        public static string UrlString(string title, MediumCatagory catagory)
        {
            string baseUrl = "https://iffr.com/nl/" + AppDelegate.FestivalYear + "/" + FolderByCatagory[catagory] + "/";
            var quotes = @"['`""]";
            var disposables = @"[./()?]";
            var strippables = @"(" + quotes + @"+\s*)|" + disposables + @"+";
            var reStrip = new Regex(strippables, RegexOptions.CultureInvariant);
            var strippedTitle = reStrip.Replace(title.ToLowerInvariant(), "");
            var extraWordChars = @"[–★]";
            var nonWords = @"[\W-" + extraWordChars + "]+";
            var reReplace = new Regex(nonWords, RegexOptions.CultureInvariant); // space or connector punctuation.
            var result = baseUrl + reReplace.Replace(strippedTitle, "-");
            return result;
        }

        public static FilmInfo TryParseUrlSummary(HttpWebRequest request, string url, MediumCatagory catagory, int filmId)
        {
            // Get the website response.
            var response = request.GetResponse() as HttpWebResponse;

            // Get the wbsite text from the response.
            var stream = new StreamReader(response.GetResponseStream());
            var text = stream.ReadToEnd();
            stream.Close();

            // Parse the website text.
            var filmInfo = TryParseText(text, catagory, filmId);

            return filmInfo;
        }

        public static FilmInfo TryParseText(string text, MediumCatagory catagory, int filmId)
        {
            var allParsesFailed = false;
            var filmDescription = string.Empty;
            var article = string.Empty;
            var ScreenedFileDescriptionByTitle = new Dictionary<string, string> { };

            // Parse the different segments as expected with this catagory.
            foreach (var parseInfo in _parseInfoByCatagory[catagory])
            {
                var success = false;

                // Carry out text replacements when available for this kind of segment.
                if (parseInfo.filterRe != null && parseInfo.filterReplacement != null)
                {
                    text = parseInfo.filterRe.Replace(text, parseInfo.filterReplacement);
                }

                // Match the regular expression for this kind of segment.
                foreach (Match match in parseInfo.re.Matches(text))
                {
                    var groupCount = match.Groups.Count;
                    string screenedFilmTitle = string.Empty;
                    for (int groupNumber = 1; groupNumber < groupCount; groupNumber++)
                    {
                        var textUnit = match.Groups[groupNumber].Value;
                        switch (parseInfo.type)
                        {
                            case ParseInfoType.Description:
                                filmDescription = textUnit;
                                break;
                            case ParseInfoType.Article:
                                article = textUnit;
                                break;
                            case ParseInfoType.ScreenedFilms:
                                if (groupNumber % 2 == 1)
                                {
                                    screenedFilmTitle = textUnit;
                                }
                                else
                                {
                                    ScreenedFileDescriptionByTitle[screenedFilmTitle] = textUnit;
                                }
                                break;
                        }
                    }
                    success = true;
                }

                // Assert if there were no matches for this segment.
                if (!success)
                {
                    allParsesFailed = true;
                }
            }

            // Throw an exception if at least one of the expected segments didn't match.
            if (allParsesFailed)
            {
                throw new UnparseblePageException(text);
            }

            // Create a Film Info instance with the information found.
            var info = new FilmInfo(filmId, Film.FilmInfoStatus.Complete, filmDescription, article);
            foreach (string title in ScreenedFileDescriptionByTitle.Keys)
            {
                info.AddScreenedFilm(title, ScreenedFileDescriptionByTitle[title]);
            }

            return info;
        }

        public static async Task<bool> VisitUrl(Film film, CancellationToken cancellationToken)
        {
            MediumCatagory catagory = film.Catagory;
            string url = film.Url;
            bool canceled = false;
            bool webErrorOccurred = false;
            WebClient httpClient = new WebClient();
            string contents = string.Empty;

            // Read the website of the given film.
            try
            {
                // Create an task to asynchroneously read the website.
                Task<string> contentsTask = httpClient.DownloadStringTaskAsync(url);

                // Return control to the calling code until the asynchronous
                // task finishes on its own thread.
                contents = await contentsTask;

                cancellationToken.ThrowIfCancellationRequested();
            }
            catch (OperationCanceledException)
            {
                canceled = true;
            }
            catch (WebException)
            {
                FilmInfo.AddNewFilmInfo(film.FilmId, Film.FilmInfoStatus.UrlError);
                webErrorOccurred = true;
            }

            // Parse the website text if no error occurred.
            if (!canceled && !webErrorOccurred)
            {
                try
                {
                    var filminfo = TryParseText(contents, catagory, film.FilmId);
                    if (filminfo != null)
                    {
                        // Add the Film Info to the list of the Screenings Plan.
                        filminfo.InfoStatus = Film.FilmInfoStatus.Complete;
                    }
                }
                catch (UnparseblePageException)
                {
                    FilmInfo.AddNewFilmInfo(film.FilmId, Film.FilmInfoStatus.ParseError);
                }
            }

            return canceled;
        }
        #endregion
    }
}
