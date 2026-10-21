# 创意技巧研究来源与能力边界

核验日期：2026-10-21。此库是依据第一手原理设计的50套操作配方，不是复制50条视频教程，也不声称本轮看完/听完或复现了50个效果。未下载创作者视频、未把示例音乐/素材许可视作可用于成片，未安装陌生GitHub代码。

证据等级：**A**=官方文档、原仓库或创作者自家正文实际可读；**B**=第一手平台搜索结果返回标题/作者/描述，页面打开受限或正文不足，未观看；**C**=仅标题/短摘要，不能支撑操作步骤；**D**=原帖受限、只能保留待复核线索，不作为实现依据。原理可查与本机可执行分开；CapCut全球版、Premiere/Fusion教程不证明国内剪映同名按钮可用。

下列摘要仅概括各来源支持的机制，50项里的具体场景、组合、轨道设计、失败判断与降级为本工作流的编辑方案推导。读目标条目的依据即可，不必每次加载全部来源。

## P01

[剪映官网：专业剪辑工具](https://www.capcut.cn/) — **A**。官方列出蒙版、关键帧等底层能力；本库网格、窗口、文字遮罩等是这些工具的组合设计，具体本机入口仍须短样片核验。

## P02

[Adobe：Adjust effect speed](https://helpx.adobe.com/premiere/desktop/add-video-effects/control-effects-and-transitions-using-keyframes/adjust-effect-speed.html) — **A**。数值/速度曲线与关键帧入出变化率的机制。不是剪映参数文档。

## P03

[Adobe：Create action speed ramps](https://www.adobe.com/creativecloud/video/hub/guides/premiere-pro-speed-ramp.html) — **A**。速度变化需平滑起止，关键动作可与快慢段结合。倒放、时间保持与其他时间结构另见G06；本库的开场/闭环是编辑方案，不声称来源逐项教授。

## P04

[Blackmagic Design：Fusion](https://www.blackmagicdesign.com/products/davinciresolve/fusion) — **A**。官方介绍2D/平面/3D跟踪、抠像和合成等；支持空间关系的原理核对。没有安装/实测Fusion时，不承诺可执行所有替代路径。

## P05

[ACMI Education：How to make a cinemagraph](https://www.acmi.net.au/education/school-program-and-resources/how-to-make-a-cinemagraph/) — **A**。定格底图与局部运动层结合，并处理首尾循环；其他抽帧/条带/翻页配方是时间采样的设计延伸。

## P06

[FFmpeg官方：filters](https://ffmpeg.org/ffmpeg-filters.html) — **A**。blend/tblend、overlay、xfade、minterpolate等给出合成/时间采样机制。查本机编译实际滤镜、alpha、色彩和时间基；本库不新增未经运行的命令。

## P07

[CreateStudio支持：Adding a Freeze-Frame Effect](https://createstudio.kayako.com/article/922-adding-a-freeze-frame-effect) — **B**。搜索索引返回其快照、独立元素及多快照克隆说明；直接打开失败，未看演示。C21/C44另有Y06蒙版克隆原理补充。

## P08

[Adobe：What is a dolly zoom](https://www.adobe.com/creativecloud/video/production/cinematography/camera-shots-and-angles/dolly-zoom-shot.html) — **B**。官方搜索摘要确认实际前后移动配合反向变焦改变透视；静机位缩放不是同一机制。

## B01

[librosa：beat_track](https://librosa.org/doc/main/api/generated/librosa.beat.beat_track.html) — **A**。音乐起音强度、速度估计与动态规划产生候选节拍；不输出导演意图或保证小节首拍。结合[原仓库](https://github.com/librosa/librosa)，ISC；未安装运行。

## B02

[CapCut：Auto Cut帮助](https://www.capcut.com/help/auto-cut-in-capcut) — **A**。自动裁切/节奏编排的概念与仅生成拍点不同；地区、设备和版本可不同，不证明国内剪映或JyWrapper具备同接口。

## B03

[librosa：onset detection](https://librosa.org/doc/main/api/generated/librosa.onset.onset_detect.html) — **A**。起音/瞬态与节拍是不同信号；动作瞬态、律动包络属于人工设计或本地分析后编排，不自动完成剪辑。

## G01

[luoluoluo22：jianying-editor-skill](https://github.com/luoluoluo22/jianying-editor-skill) — **A**。原作者剪映包装器，读取本机代码核实可用方法；不是剪映官方API。仓库外层MIT，内嵌依赖许可单独查。

## G02

[GuanYixuan：pyJianYingDraft](https://github.com/GuanYixuan/pyJianYingDraft) — **A**。原仓库关键帧/蒙版/多轨能力，Apache-2.0；本机分支和上游差异须另查，不能把JSON字段存在当已导出成功。

## G03

[gl-transitions：原规范与实现](https://github.com/gl-transitions/gl-transitions) — **A**。两输入纹理、progress和画幅处理的转场机制；仅机制参考，未安装。每个shader的许可与外部纹理许可分别确认。

## G04

[gl-transitions：luma.glsl](https://github.com/gl-transitions/gl-transitions/blob/master/transitions/luma.glsl) — **A**。灰度纹理阈值控制逐区揭示，不是光流形变或人物抠像。该文件头MIT，遮罩素材使用权另查。

## G05

[gl-transitions：directionalwarp.glsl](https://github.com/gl-transitions/gl-transitions/blob/master/transitions/directionalwarp.glsl) — **A**。方向驱动的图像扭曲/交接。该文件头MIT；先保护人物/头像，不从shader名字推定剪映有同名效果。

## G06

[Adobe：Time-stretching and time-remapping](https://helpx.adobe.com/after-effects/desktop/animate-in-after-effects/time-stretching-and-time-remapping/time-stretching-time-remapping.html) — **A**。输出时间映射到源时间；持平为保持、下降为倒放、斜率决定速度。属于机制参考，不依赖安装AE。

## G07

[Motion Canvas：tweening / flow](https://motioncanvas.io/docs/tweening/) — **A**。[flow](https://motioncanvas.io/docs/flow/)解释并行与错峰编排；[原仓库](https://github.com/motion-canvas/motion-canvas)为MIT。本库仅借鉴运动组织，不替换剪映或安装执行代码。

## G08

[Adobe：Assorted animation tools](https://helpx.adobe.com/after-effects/desktop/animate-in-after-effects/assorted-animation-tools/assorted-animation-tools.html) — **A**。运动模糊的采样窗口机制；图层运动模糊不等于视频插帧，不恢复低清细节。

## G09

[Practical-RIFE原仓库](https://github.com/hzwer/Practical-RIFE) — **A**。可选插帧原理研究，代码MIT、模型许可另查；本轮未下载权重/运行，不把生成帧叫真实拍摄高帧率。

## Y01

[Matt Loui：Motion Typography Smooth Animation in CapCut](https://www.youtube.com/watch?v=CBE1PkDRONc) — **B**。作者描述列出动态文字、跟踪、关键帧、曲线和缓动；没有观看或取得可保证复制的参数。

## Y02

[Hancybox：2D Image to 3D Parallax Effect](https://www.youtube.com/watch?v=xAQHyTDICs4) — **B**。描述明确主体PNG与背景分层动画产生视差；借鉴本地分层原理，不照搬外部AI工具上传家庭照片。

## Y03

[Make it Simple：Double Exposure Videos in CapCut](https://www.youtube.com/watch?v=ycOy5PcMOPw) — **B**。描述提到白底、抠像、第二视频和混合模式；本库双曝光需实测蒙版/alpha，不把某个混合模式保证为通解。

## Y04

[Jefe Vilanova：TEXT BEHIND A PERSON](https://www.youtube.com/watch?v=W8gL4QJUFG8) — **B**。描述支持主体前景覆盖文字的层次关系；本机遮挡/跟踪步骤未由视频验证。

## Y05

[Guidie：Keyframe Tutorial in CapCut PC](https://www.youtube.com/watch?v=gIJ8bb1fweE) — **B**。描述章节包含物体、文字、音量、颜色等关键帧；仅据章节索引，不编造剪映按钮与参数。

## Y06

[Felicia Simon：Clone people in a video — Mask function](https://www.youtube.com/watch?v=QGRsP6tmF6w) — **B**。描述/章节涉及拍摄准备、叠轨和蒙版克隆；锁机/分区是可借鉴的前提，不证明本机已复现。

## Y07

[Acer Chap：Clone Tutorial — Overlay and Mask](https://www.youtube.com/watch?v=iChCdaSawyM) — **B**。描述支持多表演、叠加、蒙版组合，不需要据此新增绿幕或云生成流程。

## Y08

[abuartss：Fast Transition — Mask & Keyframe Effects](https://www.youtube.com/watch?v=dpP70svjBwQ) — **B**。章节给出蒙版、关键帧、叠加、时机等组合主题；质量/流畅度未观看验证。

## Y09

[Hải Nam Tech：Overlay, Keyframe, and Mask](https://www.youtube.com/watch?v=0CvSIsNGlDU) — **B**。作者文字支持三类工具合成转场的主题，未提供逐帧参数。

## Y10

[Justin Odisho：Infinite Zoom Montage](https://www.youtube.com/watch?v=J76Ys8i6zVw) — **C**。只核实标题与作者，无足够操作正文；供屏内画面/递归构图的灵感索引，具体做法是本库设计。

## Y11

[Labo Des Réseaux：Auto Beat — Match your music and video](https://www.youtube.com/watch?v=ObQuGpus5hk) — **B**。描述支持AUTO BEAT音乐同步主题，不能证明自动挑镜/自动叙事。

## Y12

[feludatech：How to Auto Generate Beats](https://www.youtube.com/watch?v=TWya-74SXtc) — **B**。描述支持自动检测音乐拍点；一键精准等宣传不视作验证。

## Y13

[Gab JPM：How to freeze frame in CAPCUT](https://www.youtube.com/watch?v=l2yAlfzo9iU) — **B**。定格基础方法索引；基础定格本身未单独计入本次50项进阶配方。

## Y14

[Speed Ramp in CapCut PC（作者未核实）](https://www.youtube.com/watch?v=esvkARN740Y) — **C**。仅题名；不作为参数依据。

## Y15

[Picture-in-Picture in CapCut App（作者未核实）](https://www.youtube.com/watch?v=y1cylbwop_Q) — **C**。仅移动版画中画摘要；不据此写国内桌面版操作路径。

## Y16

[Zeven 7：Keyframe Mastery Guide](https://www.youtube.com/watch?v=fKNDlT5JbTY) — **B**。原描述/章节含图表曲线、颜色变化和回弹动画；仅原平台文字核验。

## F01

[Cinecom：Freeze Frame Introduction](https://www.cinecom.net/adobe-premiere-pro-tutorials/video-effects/freeze-frame-introduction/) — **A**。创作者正文给出静帧、抠像、图形背景、主体运动与姓名层等；本库使用合成结构，不搬其素材或参数。

## F02

[Cinecom：3D freeze effect](https://www.cinecom.net/adobe-after-effects-tutorials/freeze-frame-khaled-postmalone/) — **A**。创作者正文含表演者保持姿势而摄影机移动的拍摄方案；不代表单帧自动重建3D。

## F03

[Cinecom：5 Editing Tricks You Should Learn IMMEDIATELY](https://www.cinecom.net/adobe-premiere-pro-tutorials/audio-effects/5-editing-tricks-learn-immediately/) — **A**。正文涉及拍点、音乐结尾、低通和Automate to Sequence；剪映替代必须另验，不混淆Premiere功能。

## T01

[TikTok Shop Academy：Basics of Editing Part One](https://seller-uk.tiktok.com/university/course?content_id=978434743060256&learning_id=965808395667232) — **A**。平台自己的编辑课程支持按音乐与合理时机剪辑；本库不继承其广告投放或商业音乐授权。

## T02

[TikTok Notes：bearbykim Auto Cut](https://notes.tiktok.com/%40bearbykim/7442384816399581697?region=th) — **B**。原平台搜索文字为选素材、选风格的AutoCut经历；不是国内剪映桌面支持证明，未观看。

## Instagram / TikTok待复核原帖

以下平台已实际检索和尝试访问，但页面受限；不引用镜像正文来替代第一手验证，不把它们当已学会或已复现的证据。后续入口恢复时再补完整观察。

- **D** [Instagram / iamjusthaidi：Multi-Clone线索](https://www.instagram.com/reel/DWyUTgSCMY6/)：原页限流，待核实。
- **D** [TikTok / duekneel：定格人物介绍线索](https://www.tiktok.com/@duekneel/video/7343646244692086018)：原页受限。
- **D** [TikTok / duekneel：卡点线索](https://www.tiktok.com/@duekneel/video/7308241618916740353)：原页内容未核实。
- **B/D** [TikTok Notes / rose_lushlife：定格线索](https://notes.tiktok.com/%40rose_lushlife/7508950712995398145?region=id)：原平台搜索摘要可见，直接打开超时，未观看。

## 使用前再核实

引用教程不等于获得视频、配乐、模板或字体使用权。GitHub仅用原仓库/原实现，逐项核代码与素材许可；本轮未克隆或执行研究仓库。优先读本机已安装工具，未知草稿字段不试写用户工程。实现状态与研究来源等级分别记录。
