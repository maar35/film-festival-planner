using System;
using System.Collections.Generic;
using System.IO;

namespace PresentScreenings.TableView
{
	/// <summary>
    /// List reader, read a file and return is list of generic objects.
    /// </summary>

    public class ListReader<T> where T : class
	{
		#region Private Members
		string _fileName;
		bool _skipHeader;
		#endregion

		#region Constructors
		public ListReader(string fileName, bool skipHeader = false)
		{
			_fileName = fileName;
			_skipHeader = skipHeader;
		}
		#endregion

		#region Public Methods
		public List<T> ReadListFromFile(Func<string, T> TConstructor)
		{
			var resultList = new List<T> { };

			using (var streamReader = OpenStream(_fileName))
			{
				string line;
				bool headerToBeSkipped = _skipHeader;
				while ((line = streamReader.ReadLine()) != null)
				{
					if (headerToBeSkipped)
					{
						headerToBeSkipped = false;
						continue;
					}
					resultList.Add(TConstructor(line));
				}
			}

			return resultList;
		}
		#endregion

		#region Private Methods
		private StreamReader OpenStream(string url)
		{
			FileStream fileStream;

			try
			{
				fileStream = new FileStream(url, FileMode.Open, FileAccess.Read);
			}
			catch (Exception ex)
			{
				throw new Exception(string.Format("Read error, couldn't access file {0}", url), ex);
			}

			return new StreamReader(fileStream);
		}
		#endregion
	}
}
