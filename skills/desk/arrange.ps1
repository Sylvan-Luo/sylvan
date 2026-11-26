# 桌面图标排列：按「项目类型」再按「名称」排序（文件夹在前、同类放一起），并打开「自动排列」「对齐到网格」。
# 等于在桌面右键 → 排序方式 → 项目类型 + 查看 → 自动排列图标 / 将图标与网格对齐。经 COM 调桌面的 IFolderView2。
# 参数：$IN.sort = 'type'（默认）或 'name'
$src = @'
using System;
using System.Runtime.InteropServices;

namespace DeskArrange {
  [ComImport, Guid("85CB6900-4D95-11CF-960C-0080C7F4EE85"), InterfaceType(ComInterfaceType.InterfaceIsDual)]
  public interface IShellWindows {
    int Count { get; }
    [return: MarshalAs(UnmanagedType.IDispatch)] object Item(object index);
    [return: MarshalAs(UnmanagedType.IUnknown)] object _NewEnum();
    int Register([MarshalAs(UnmanagedType.IDispatch)] object pid, int hwnd, int swClass);
    int RegisterPending(int lThreadId, ref object pvarloc, ref object pvarlocRoot, int swClass);
    void Revoke(int lCookie);
    void OnNavigate(int lCookie, ref object pvarLoc);
    void OnActivated(int lCookie, bool fActive);
    [return: MarshalAs(UnmanagedType.IDispatch)]
    object FindWindowSW(ref object pvarLoc, ref object pvarLocRoot, int swClass, out int phwnd, int swfwOptions);
    void OnCreated(int lCookie, [MarshalAs(UnmanagedType.IUnknown)] object punk);
    bool ProcessAttachDetach(bool fAttach);
  }
  [ComImport, Guid("9BA05972-F6A8-11CF-A442-00A0C90A8F39")] public class ShellWindows { }

  [ComImport, Guid("6D5140C1-7436-11CE-8034-00AA006009FA"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
  public interface IServiceProvider {
    [return: MarshalAs(UnmanagedType.IUnknown)] object QueryService(ref Guid sid, ref Guid iid);
  }

  [ComImport, Guid("000214E2-0000-0000-C000-000000000046"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
  public interface IShellBrowser {
    void GetWindow(); void ContextSensitiveHelp(); void InsertMenusSB(); void SetMenuSB(); void RemoveMenusSB();
    void SetStatusTextSB(); void EnableModelessSB(); void TranslateAcceleratorSB(); void BrowseObject();
    void GetViewStateStream(); void GetControlWindow(); void SendControlMsg();
    [return: MarshalAs(UnmanagedType.IUnknown)] object QueryActiveShellView();
  }

  [StructLayout(LayoutKind.Sequential)]
  public struct SORTCOLUMN { public Guid fmtid; public uint pid; public int direction; }

  [ComImport, Guid("1af3a467-214f-4298-908e-06b03e0b39f9"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
  public interface IFolderView2 {
    // IFolderView（不用的只占位）
    void GetCurrentViewMode(); void SetCurrentViewMode(); void GetFolder(); void Item(); void ItemCount();
    void Items(); void GetSelectionMarkedItem(); void GetFocusedItem(); void GetItemPosition(); void GetSpacing();
    void GetDefaultSpacing(); void GetAutoArrange(); void SelectItem(); void SelectAndPositionItems();
    // IFolderView2
    void SetGroupBy(); void GetGroupBy(); void SetViewProperty(); void GetViewProperty();
    void SetTileViewProperties(); void SetExtendedTileViewProperties(); void SetText();
    void SetCurrentFolderFlags(uint dwMask, uint dwFlags);
    uint GetCurrentFolderFlags();
    int GetSortColumnCount();
    void SetSortColumns([MarshalAs(UnmanagedType.LPArray)] SORTCOLUMN[] rgSortColumns, int cColumns);
  }

  public static class Desk {
    public static string Arrange(bool byType) {
      IShellWindows sw = (IShellWindows)new ShellWindows();
      object loc = 0, root = null; int hwnd;   // CSIDL_DESKTOP, SWC_DESKTOP=8, SWFO_NEEDDISPATCH=1
      object disp = sw.FindWindowSW(ref loc, ref root, 8, out hwnd, 1);
      Guid sid = new Guid("4C96BE40-915C-11CF-99D3-00AA004AE837"), iid = typeof(IShellBrowser).GUID;
      IShellBrowser sb = (IShellBrowser)((IServiceProvider)disp).QueryService(ref sid, ref iid);
      IFolderView2 fv = (IFolderView2)sb.QueryActiveShellView();
      Guid sys = new Guid("B725F130-47EF-101A-A5F1-02608C9EEBAC");   // PKEY_ItemTypeText=4, PKEY_ItemNameDisplay=10
      SORTCOLUMN type = new SORTCOLUMN { fmtid = sys, pid = 4, direction = 1 };
      SORTCOLUMN name = new SORTCOLUMN { fmtid = sys, pid = 10, direction = 1 };
      SORTCOLUMN[] cols = byType ? new[] { type, name } : new[] { name };
      fv.SetSortColumns(cols, cols.Length);
      const uint AUTO = 0x1, SNAP = 0x80000;                           // FWF_AUTOARRANGE | FWF_SNAPTOGRID
      fv.SetCurrentFolderFlags(AUTO | SNAP, AUTO | SNAP);
      return "flags=0x" + fv.GetCurrentFolderFlags().ToString("X");
    }
  }
}
'@
if (-not ('DeskArrange.Desk' -as [type])) { Add-Type -TypeDefinition $src }
$byType = -not ($IN -and $IN.sort -eq 'name')
if ([Threading.Thread]::CurrentThread.ApartmentState -eq 'STA') {
  $msg = [DeskArrange.Desk]::Arrange($byType)
} else {
  $r = $null
  $t = New-Object Threading.Thread([Threading.ThreadStart]{ $script:r = [DeskArrange.Desk]::Arrange($byType) })
  $t.SetApartmentState('STA'); $t.Start(); $t.Join(); $msg = $script:r
}
$OUT = [ordered]@{ ok = $true; msg = $msg }
